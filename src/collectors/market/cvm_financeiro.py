"""Coletor CVM — dados financeiros das usinas de capital aberto."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime

CVM_DFP_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/dfp_cia_aberta_{ano}.zip"

CNPJ_EMPRESA = {
    "51466860000156": "sao_martinho",
    "02635522000158": "jalles",
    "08070508000178": "cosan",
    "07689002000189": "raizen",
}

CONTAS = {
    "3.01": ("receita", "Receita"),
    "3.11": ("lucro_liquido", "Lucro"),
    "2.01": ("passivo_circulante", "Passivo Circulante"),
    "2.02": ("passivo_nao_circulante", "Passivo Nao Circulante"),
}


def _num(valor):
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


def parse_csv_cvm(conteudo):
    out = []
    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=";")
    for linha in leitor:
        cnpj_raw = linha.get("CNPJ_CIA", "") or ""
        cnpj = re.sub(r"[./-]", "", cnpj_raw).strip()
        empresa = CNPJ_EMPRESA.get(cnpj)
        if not empresa:
            continue
        if (linha.get("ORDEM_EXERC", "") or "").strip().upper() not in ("ULTIMO", "\u00daLTIMO"):
            continue
        conta = (linha.get("CD_CONTA", "") or "").strip()
        if conta not in CONTAS:
            continue
        metric, _ = CONTAS[conta]
        valor = _num(linha.get("VL_CONTA", ""))
        if valor is None:
            continue
        escala = (linha.get("ESCALA_MOEDA", "") or "").strip().lower()
        unidade = "R$ mil" if "mil" in escala else "R$"
        ref = (linha.get("DT_FIM_EXERC", "") or "").strip()
        try:
            data_ref = datetime.strptime(ref, "%Y-%m-%d").date()
        except ValueError:
            data_ref = None
        out.append({"company": empresa, "metric": metric, "valor": valor,
                    "unidade": unidade, "data_referencia": data_ref})
    return out


def consolidar_divida(linhas):
    extras = {}
    for r in linhas:
        if r["metric"] in ("passivo_circulante", "passivo_nao_circulante"):
            chave = (r["company"], r["data_referencia"], r["unidade"])
            extras[chave] = extras.get(chave, 0.0) + r["valor"]
    _passivos = ("passivo_circulante", "passivo_nao_circulante")
    saida = [r for r in linhas if r["metric"] not in _passivos]
    for (company, data_ref, unidade), total in extras.items():
        saida.append({"company": company, "metric": "divida_total",
                      "valor": round(total, 2), "unidade": unidade, "data_referencia": data_ref})
    return saida


import zipfile  # noqa: E402
from datetime import datetime as _dt  # noqa: E402

import httpx  # noqa: E402

from src.domain.models import CollectorResult  # noqa: E402
from src.persistence.repositories import log_run, upsert_company_metrics  # noqa: E402

SOURCE_CODE = "cvm"


class CvmFinanceiroCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def __init__(self, ano=None):
        self.ano = ano or _dt.today().year

    def collect(self):
        url = CVM_DFP_URL.format(ano=self.ano)
        resp = httpx.get(url, timeout=120, headers={"User-Agent": "canavis/0.1"})
        resp.raise_for_status()
        linhas = []
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            alvos = [n for n in z.namelist()
                     if ("DRE_con" in n or "BPP_con" in n) and n.endswith(".csv")]
            for nome in alvos:
                with z.open(nome) as f:
                    conteudo = f.read().decode("latin-1")
                linhas.extend(parse_csv_cvm(conteudo))
        linhas = consolidar_divida(linhas)
        for r in linhas:
            r["grupo"] = "financeiro"
            r["fonte"] = "cvm_dfp"
            r["periodo"] = str(r.get("data_referencia") or self.ano)
            r["collector_version"] = self.version
            r["status_validacao"] = "a_conferir"
            r["url_original"] = url
        return linhas

    def run(self):
        started = _dt.utcnow()
        try:
            linhas = self.collect()
            new = upsert_company_metrics(linhas)
            result = CollectorResult(source_code=self.source_code, started_at=started,
                                     finished_at=_dt.utcnow(), rows_seen=len(linhas),
                                     rows_new=new, ok=True)
        except Exception as exc:
            result = CollectorResult(source_code=self.source_code, started_at=started,
                                     finished_at=_dt.utcnow(), ok=False,
                                     error=f"{type(exc).__name__}: {exc}")
        log_run(result)
        return result
