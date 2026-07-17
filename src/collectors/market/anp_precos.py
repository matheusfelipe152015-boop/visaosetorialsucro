"""Coletor ANP — preços de combustíveis (revenda), nacional e por estado.

Fonte: ANP, Série Histórica de Preços de Combustíveis (dados abertos, CC0).
CSV mensal, separador ';', decimal ',', encoding latin-1, uma linha por posto.
Colunas usadas: 'Estado - Sigla', 'Produto', 'Valor de Venda', 'Data da Coleta'.

Guarda TRÊS coisas:
  1. média nacional por combustível  -> indicator_values (KPIs);
  2. média por ESTADO                -> metricas_uf (alimenta o mapa);
  3. PARIDADE etanol/gasolina por UF -> metricas_uf (o driver da demanda).

Sobre a paridade: se o etanol custa menos de ~70% do preço da gasolina,
compensa abastecer com etanol (rende menos por litro, mas sai mais barato).
Acima disso, o consumidor tende a preferir gasolina — demanda de etanol cai.

Nota: no início do mês o arquivo do mês corrente ainda não existe (404). O
coletor tenta o mês atual e, se não houver, cai para o mês anterior.
"""

from __future__ import annotations

import io
import uuid
from datetime import date, datetime

import httpx
import pandas as pd
from sqlalchemy import text

from src.collectors.base import Collector
from src.domain.enums import ValidationStatus
from src.domain.models import CollectorResult, IndicatorValue
from src.persistence.db import get_engine
from src.persistence.repositories import log_run, upsert_indicator_values
from src.services.chuva import REGIAO_POR_UF

SOURCE_CODE = "anp"

# A ANP não mantém um padrão único de nome de arquivo. O mais confiável é o
# "últimas 4 semanas", que tem endereço FIXO e é atualizado sempre. Os mensais
# mudaram de padrão entre 2025 e 2026 (e às vezes saem como .xlsx). Por isso
# tentamos uma lista de candidatos, em ordem, até um funcionar.
ANP_BASE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc"

ANP_URL_4SEMANAS = f"{ANP_BASE}/qus/ultimas-4-semanas-gasolina-etanol.csv"
# padrões mensais conhecidos ({ano}, {mes})
ANP_MENSAIS = (
    f"{ANP_BASE}/dsan/{{ano}}/{{mes:02d}}-dados-abertos-precos-gasolina-etanol.csv",
    f"{ANP_BASE}/dsan/{{ano}}/precos-gasolina-etanol-{{mes:02d}}.csv",
    f"{ANP_BASE}/dsan/{{ano}}/{{ano}}-{{mes:02d}}-gasolina-etanol.csv",
)

PRODUTO_INDICADOR: dict[str, tuple[str, str]] = {
    "GASOLINA": ("preco_gasolina", "Gasolina comum (revenda)"),
    "GASOLINA ADITIVADA": ("preco_gasolina_aditivada", "Gasolina aditivada (revenda)"),
    "ETANOL": ("preco_etanol", "Etanol hidratado (revenda)"),
}

def _ler_csv(csv_bytes: bytes) -> pd.DataFrame:
    """Lê o CSV da ANP tolerando variações de encoding e nomes de coluna."""
    ultimo_erro: Exception | None = None
    for enc in ("latin-1", "utf-8", "utf-8-sig"):
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes), sep=";", decimal=",", encoding=enc)
            break
        except Exception as exc:  # noqa: BLE001 — tenta o próximo encoding
            ultimo_erro = exc
    else:
        raise ultimo_erro if ultimo_erro else RuntimeError("CSV da ANP ilegível")

    df.columns = [str(c).strip() for c in df.columns]

    # nomes variam entre arquivos; normalizamos para os que usamos
    def _achar(*candidatos: str) -> str | None:
        for c in df.columns:
            alvo = c.lower().replace("ç", "c").replace("ã", "a").replace("é", "e")
            for cand in candidatos:
                if cand in alvo:
                    return c
        return None

    col_uf = _achar("estado - sigla", "estado", "uf")
    col_prod = _achar("produto")
    col_valor = _achar("valor de venda", "valor venda", "preco de venda")
    col_data = _achar("data da coleta", "data coleta")
    # o estado é opcional: sem ele ainda dá para calcular a média nacional
    faltando = [n for n, c in
                (("produto", col_prod), ("valor", col_valor), ("data", col_data))
                if c is None]
    if faltando:
        raise RuntimeError(f"CSV da ANP sem colunas esperadas: {', '.join(faltando)}")

    renomear = {
        col_prod: "Produto", col_valor: "Valor de Venda", col_data: "Data da Coleta",
    }
    if col_uf:
        renomear[col_uf] = "uf"
    df = df.rename(columns=renomear)
    if "uf" not in df.columns:
        df["uf"] = None
    else:
        df["uf"] = df["uf"].astype(str).str.strip().str.upper()
    df["Produto"] = df["Produto"].astype(str).str.upper().str.strip()
    df["Valor de Venda"] = pd.to_numeric(
        df["Valor de Venda"].astype(str).str.replace(",", ".", regex=False), errors="coerce"
    )
    df["data_ref"] = pd.to_datetime(
        df["Data da Coleta"], dayfirst=True, errors="coerce"
    ).dt.date
    return df.dropna(subset=["Valor de Venda", "data_ref"])


def parse_precos(csv_bytes: bytes) -> list[IndicatorValue]:
    """Média NACIONAL por combustível, por data de coleta."""
    df = _ler_csv(csv_bytes)
    out: list[IndicatorValue] = []
    for produto, (code, _nome) in PRODUTO_INDICADOR.items():
        sub = df[df["Produto"] == produto]
        if sub.empty:
            continue
        for ref, grupo in sub.groupby("data_ref"):
            media = float(grupo["Valor de Venda"].mean())
            out.append(
                IndicatorValue(
                    indicator_code=code,
                    source_code=SOURCE_CODE,
                    data_referencia=ref,
                    valor=round(media, 4),
                    unidade="R$/L",
                    moeda="BRL",
                    escala="unit",
                    data_publicacao=ref,
                    data_coleta=datetime.utcnow(),
                    collector_version="0.1.0",
                    status_validacao=ValidationStatus.OK,
                    url_original="https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos",
                )
            )
    return out


def parse_precos_uf(csv_bytes: bytes) -> list[dict]:
    """Média por ESTADO no período + PARIDADE etanol/gasolina por estado.

    Devolve linhas {uf, regiao, periodo, metric, valor, unidade, data_referencia}.
    O período é o mês da pesquisa (ex.: '2026-06').
    """
    df = _ler_csv(csv_bytes)
    df = df[df["uf"].notna()]
    if df.empty:
        return []  # sem coluna de estado -> sem mapa
    ref = max(df["data_ref"])              # data mais recente do arquivo
    periodo = ref.strftime("%Y-%m")

    out: list[dict] = []
    medias: dict[tuple[str, str], float] = {}  # (uf, code) -> preço médio

    for produto, (code, _nome) in PRODUTO_INDICADOR.items():
        sub = df[df["Produto"] == produto]
        if sub.empty:
            continue
        for uf, grupo in sub.groupby("uf"):
            uf = str(uf).strip().upper()
            media = round(float(grupo["Valor de Venda"].mean()), 4)
            medias[(uf, code)] = media
            out.append({
                "uf": uf, "regiao": REGIAO_POR_UF.get(uf), "periodo": periodo,
                "metric": code, "valor": media, "unidade": "R$/L",
                "data_referencia": ref,
            })

    # paridade etanol/gasolina por estado (%): abaixo de ~70% o etanol compensa
    ufs = {uf for (uf, _c) in medias}
    for uf in sorted(ufs):
        etanol = medias.get((uf, "preco_etanol"))
        gasolina = medias.get((uf, "preco_gasolina"))
        if etanol and gasolina:
            paridade = round(etanol / gasolina * 100, 1)
            out.append({
                "uf": uf, "regiao": REGIAO_POR_UF.get(uf), "periodo": periodo,
                "metric": "paridade_etanol", "valor": paridade, "unidade": "%",
                "data_referencia": ref,
            })
    return out


def upsert_metricas_uf(linhas: list[dict]) -> int:
    """Grava métricas por estado (idempotente)."""
    eng = get_engine()
    agora = datetime.utcnow()
    novos = 0
    with eng.begin() as conn:
        for r in linhas:
            existe = conn.execute(
                text("SELECT 1 FROM metricas_uf WHERE uf=:u AND periodo=:p "
                     "AND metric=:m AND source_code=:src"),
                {"u": r["uf"], "p": r["periodo"], "m": r["metric"], "src": SOURCE_CODE},
            ).first()
            if not existe:
                novos += 1
            conn.execute(
                text("""INSERT INTO metricas_uf(id,uf,regiao,periodo,metric,valor,unidade,
                          data_referencia,source_code,data_coleta,collector_version,
                          status_validacao,url_original)
                        VALUES(:id,:u,:rg,:p,:m,:v,:un,:dr,:src,:dc,:cv,:st,:url)
                        ON CONFLICT(uf,periodo,metric,source_code) DO UPDATE SET
                          valor=excluded.valor, data_coleta=excluded.data_coleta"""),
                {"id": uuid.uuid4().hex, "u": r["uf"], "rg": r["regiao"], "p": r["periodo"],
                 "m": r["metric"], "v": r["valor"], "un": r["unidade"],
                 "dr": r["data_referencia"], "src": SOURCE_CODE, "dc": agora,
                 "cv": "0.1.0", "st": "ok",
                 "url": "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos"},
            )
    return novos


class AnpPrecosCollector(Collector):
    source_code = SOURCE_CODE
    version = "0.2.0"

    def __init__(self, ano: int | None = None, mes: int | None = None) -> None:
        hoje = date.today()
        self.ano = ano or hoje.year
        self.mes = mes or hoje.month

    def _candidatos(self) -> list[str]:
        """URLs a tentar, em ordem: fixa (4 semanas) e depois mensais."""
        urls = [ANP_URL_4SEMANAS]
        meses = [(self.ano, self.mes)]
        if self.mes > 1:
            meses.append((self.ano, self.mes - 1))
        else:
            meses.append((self.ano - 1, 12))
        if self.mes > 2:
            meses.append((self.ano, self.mes - 2))
        for ano, mes in meses:
            for padrao in ANP_MENSAIS:
                urls.append(padrao.format(ano=ano, mes=mes))
        return urls

    def _baixar(self) -> bytes:
        """Tenta cada candidato até um responder. Guarda a URL que funcionou."""
        erro_final: Exception | None = None
        for url in self._candidatos():
            try:
                resp = httpx.get(
                    url, timeout=120, follow_redirects=True,
                    headers={"User-Agent": "visaosetorialsucro/0.1 (intel-sucroenergetico)"},
                )
                resp.raise_for_status()
                if not resp.content or len(resp.content) < 200:
                    continue  # arquivo vazio/placeholder
                self.url_usada = url
                return resp.content
            except Exception as exc:  # noqa: BLE001 — tenta o próximo candidato
                erro_final = exc
                continue
        if erro_final:
            raise erro_final
        raise RuntimeError("ANP indisponível (nenhum arquivo encontrado)")

    def collect(self) -> tuple[list[IndicatorValue], list[dict]]:
        conteudo = self._baixar()
        return parse_precos(conteudo), parse_precos_uf(conteudo)

    def run(self) -> CollectorResult:
        started = datetime.utcnow()
        try:
            nacional, por_uf = self.collect()
            n1 = upsert_indicator_values(nacional)
            n2 = upsert_metricas_uf(por_uf)
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(),
                rows_seen=len(nacional) + len(por_uf), rows_new=n1 + n2, ok=True,
            )
        except Exception as exc:  # noqa: BLE001
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        log_run(result)
        return result
