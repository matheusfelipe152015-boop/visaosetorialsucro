"""Coletor CVM — dados financeiros das usinas de capital aberto.

Fonte: Portal de Dados Abertos da CVM (dados.cvm.gov.br). As companhias abertas
entregam demonstrações financeiras padronizadas (DFP, anual) e trimestrais
(ITR). Os arquivos são públicos, padronizados e sem cadastro.

Estratégia:
  1. baixar o arquivo anual de DFP (um .zip com todas as companhias);
  2. dentro dele, ler a Demonstração do Resultado (DRE) e o Balanço (BPP);
  3. filtrar só as nossas usinas (por CNPJ / nome);
  4. extrair receita líquida, lucro líquido e passivo (endividamento).

Como o ambiente de desenvolvimento não tem internet, o PARSE é separado do
download e testado offline (ver tests/test_cvm.py). A coleta real roda na
máquina do usuário / no robô.

Arquivos DFP (exemplo 2026):
  https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_2026.zip
Dentro do zip, os CSVs de interesse (separador ';', encoding latin-1):
  - dfp_cia_aberta_DRE_con_AAAA.csv  (Demonstração de Resultado, consolidado)
  - dfp_cia_aberta_BPP_con_AAAA.csv  (Balanço Patrimonial Passivo, consolidado)
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime

CVM_DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"

# CNPJ (só dígitos) -> code interno da empresa. Usado para filtrar do arquivo
# gigante da CVM só as nossas usinas.
CNPJ_EMPRESA: dict[str, str] = {
    "51466860000156": "sao_martinho",   # São Martinho S.A.
    "02635522000158": "jalles",         # Jalles Machado S.A.
    "08070508000178": "cosan",          # Cosan S.A.
    "07689002000189": "raizen",         # Raízen S.A.
}

# Contas da CVM (código padronizado CD_CONTA) que nos interessam.
# Estes códigos são padronizados no plano de contas da CVM.
CONTAS = {
    "3.01": ("receita", "Receita de Venda de Bens e/ou Serviços"),
    "3.11": ("lucro_liquido", "Lucro/Prejuízo Consolidado do Período"),
    "2.01": ("passivo_circulante", "Passivo Circulante"),
    "2.02": ("passivo_nao_circulante", "Passivo Não Circulante"),
}


def _num(valor: str) -> float | None:
    """Converte o valor da CVM para float, tratando o ponto corretamente.

    A CVM pode trazer ponto como separador DECIMAL (ex.: '6431765.00') ou, em
    alguns exportadores, como separador de MILHAR ('6.431.765'). Distinguimos:
      - tem vírgula  -> formato BR: ponto = milhar, vírgula = decimal;
      - só pontos, todos os grupos após o 1º com 3 dígitos -> milhar;
      - caso contrário -> ponto é decimal.
    """
    v = (valor or "").strip()
    if not v or v == "-":
        return None
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    elif "." in v:
        partes = v.split(".")
        if all(len(p) == 3 for p in partes[1:]):
            v = v.replace(".", "")
    try:
        return float(v)
    except ValueError:
        return None


def parse_csv_cvm(conteudo: str) -> list[dict]:
    """Lê um CSV da CVM (separador ';') e devolve as linhas das nossas usinas.

    Cada linha de saída: {company, metric, valor, data_referencia, unidade}.
    Só considera a coluna do ÚLTIMO exercício (ORDEM_EXERC = 'ÚLTIMO') e contas
    de interesse.
    """
    out: list[dict] = []
    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=";")
    for linha in leitor:
        cnpj_raw = linha.get("CNPJ_CIA", "") or ""
        cnpj = re.sub(r"[./-]", "", cnpj_raw).strip()
        empresa = CNPJ_EMPRESA.get(cnpj)
        if not empresa:
            continue
        if (linha.get("ORDEM_EXERC", "") or "").strip().upper() not in ("ÚLTIMO", "ULTIMO"):
            continue
        conta = (linha.get("CD_CONTA", "") or "").strip()
        if conta not in CONTAS:
            continue
        metric, _ = CONTAS[conta]
        valor = _num(linha.get("VL_CONTA", ""))
        if valor is None:
            continue
        # a CVM informa a escala em VL_CONTA já na unidade indicada (geralmente milhares)
        escala = (linha.get("ESCALA_MOEDA", "") or "").strip().lower()
        unidade = "R$ mil" if "mil" in escala else "R$"
        ref = (linha.get("DT_FIM_EXERC", "") or "").strip()
        try:
            data_ref = datetime.strptime(ref, "%Y-%m-%d").date()
        except ValueError:
            data_ref = None
        out.append(
            {
                "company": empresa,
                "metric": metric,
                "valor": valor,
                "unidade": unidade,
                "data_referencia": data_ref,
            }
        )
    return out


def consolidar_divida(linhas: list[dict]) -> list[dict]:
    """Soma passivo circulante + não circulante em 'divida_total' por empresa/data."""
    extras: dict[tuple, float] = {}
    for r in linhas:
        if r["metric"] in ("passivo_circulante", "passivo_nao_circulante"):
            chave = (r["company"], r["data_referencia"], r["unidade"])
            extras[chave] = extras.get(chave, 0.0) + r["valor"]
    _passivos = ("passivo_circulante", "passivo_nao_circulante")
    saida = [r for r in linhas if r["metric"] not in _passivos]
    for (company, data_ref, unidade), total in extras.items():
        saida.append(
            {
                "company": company,
                "metric": "divida_total",
                "valor": round(total, 2),
                "unidade": unidade,
                "data_referencia": data_ref,
            }
        )
    return saida


# ── coleta real (baixa o zip, extrai CSVs, parseia, grava) ─────────────────
import zipfile  # noqa: E402

import httpx  # noqa: E402

from src.domain.models import CollectorResult  # noqa: E402
from src.persistence.repositories import log_run, upsert_company_metrics  # noqa: E402

SOURCE_CODE = "cvm"


class CvmFinanceiroCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def __init__(self, ano: int | None = None) -> None:
        self.ano = ano or datetime.today().year

    def collect(self) -> list[dict]:
        url = CVM_DFP_URL.format(ano=self.ano)
        resp = httpx.get(url, timeout=120, headers={"User-Agent": "visaosetorialsucro/0.1"})
        resp.raise_for_status()
        linhas: list[dict] = []
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            # arquivos consolidados de DRE (resultado) e BPP (passivo)
            alvos = [
                n for n in z.namelist()
                if ("DRE_con" in n or "BPP_con" in n) and n.endswith(".csv")
            ]
            for nome in alvos:
                with z.open(nome) as f:
                    conteudo = f.read().decode("latin-1")
                linhas.extend(parse_csv_cvm(conteudo))
        linhas = consolidar_divida(linhas)
        # anota metadados de gravação
        for r in linhas:
            r["grupo"] = "financeiro"
            r["fonte"] = "cvm_dfp"
            r["periodo"] = str(r.get("data_referencia") or self.ano)
            r["collector_version"] = self.version
            r["status_validacao"] = "a_conferir"  # dado auto-extraído: conferir
            r["url_original"] = url
        return linhas

    def run(self) -> CollectorResult:
        started = datetime.utcnow()
        try:
            linhas = self.collect()
            new = upsert_company_metrics(linhas)
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), rows_seen=len(linhas), rows_new=new, ok=True,
            )
        except Exception as exc:  # noqa: BLE001 — falha de fonte não derruba o job
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), ok=False, error=f"{type(exc).__name__}: {exc}",
            )
        log_run(result)
        return result
