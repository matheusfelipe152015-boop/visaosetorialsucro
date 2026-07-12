"""Coletor ANP — precos de combustiveis (revenda), nacional e por estado.

Guarda: (1) media nacional -> indicator_values; (2) media por ESTADO e
(3) PARIDADE etanol/gasolina por UF -> metricas_uf (alimentam o mapa).

Paridade: se o etanol custa menos de ~70% da gasolina, compensa abastecer
com etanol. Acima disso, o consumidor migra para gasolina.

No inicio do mes o arquivo do mes corrente ainda nao existe (404); o coletor
cai para o mes anterior automaticamente.
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

ANP_BASE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc"

ANP_URL_4SEMANAS = f"{ANP_BASE}/qus/ultimas-4-semanas-gasolina-etanol.csv"
ANP_MENSAIS = (
    f"{ANP_BASE}/dsan/{{ano}}/{{mes:02d}}-dados-abertos-precos-gasolina-etanol.csv",
    f"{ANP_BASE}/dsan/{{ano}}/precos-gasolina-etanol-{{mes:02d}}.csv",
    f"{ANP_BASE}/dsan/{{ano}}/{{ano}}-{{mes:02d}}-gasolina-etanol.csv",
)

PRODUTO_INDICADOR = {
    "GASOLINA": ("preco_gasolina", "Gasolina comum (revenda)"),
    "GASOLINA ADITIVADA": ("preco_gasolina_aditivada", "Gasolina aditivada (revenda)"),
    "ETANOL": ("preco_etanol", "Etanol hidratado (revenda)"),
}

def _ler_csv(csv_bytes):
    """Le o CSV da ANP tolerando variacoes de encoding e nomes de coluna."""
    ultimo_erro = None
    df = None
    for enc in ("latin-1", "utf-8", "utf-8-sig"):
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes), sep=";", decimal=",", encoding=enc)
            break
        except Exception as exc:
            ultimo_erro = exc
    if df is None:
        raise ultimo_erro if ultimo_erro else RuntimeError("CSV da ANP ilegivel")

    df.columns = [str(c).strip() for c in df.columns]

    def _achar(*candidatos):
        for c in df.columns:
            alvo = c.lower().replace("\u00e7", "c").replace("\u00e3", "a")
            for cand in candidatos:
                if cand in alvo:
                    return c
        return None

    col_uf = _achar("estado - sigla", "estado", "uf")
    col_prod = _achar("produto")
    col_valor = _achar("valor de venda", "valor venda", "preco de venda")
    col_data = _achar("data da coleta", "data coleta")
    faltando = [n for n, c in
                (("produto", col_prod), ("valor", col_valor), ("data", col_data))
                if c is None]
    if faltando:
        raise RuntimeError("CSV da ANP sem colunas: " + ", ".join(faltando))

    renomear = {col_prod: "Produto", col_valor: "Valor de Venda", col_data: "Data da Coleta"}
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


def parse_precos(csv_bytes):
    """Media NACIONAL por combustivel, por data de coleta."""
    df = _ler_csv(csv_bytes)
    out = []
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


def parse_precos_uf(csv_bytes):
    """Media por ESTADO + PARIDADE etanol/gasolina por estado."""
    df = _ler_csv(csv_bytes)
    df = df[df["uf"].notna()]
    if df.empty:
        return []
    ref = max(df["data_ref"])
    periodo = ref.strftime("%Y-%m")

    out = []
    medias = {}

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


def upsert_metricas_uf(linhas):
    """Grava metricas por estado (idempotente)."""
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

    def __init__(self, ano=None, mes=None):
        hoje = date.today()
        self.ano = ano or hoje.year
        self.mes = mes or hoje.month

    def _candidatos(self):
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

    def _baixar(self):
        """Tenta cada candidato ate um responder."""
        erro_final = None
        for url in self._candidatos():
            try:
                resp = httpx.get(
                    url, timeout=120, follow_redirects=True,
                    headers={"User-Agent": "canavis/0.1 (intel-sucroenergetico)"},
                )
                resp.raise_for_status()
                if not resp.content or len(resp.content) < 200:
                    continue
                self.url_usada = url
                return resp.content
            except Exception as exc:
                erro_final = exc
                continue
        if erro_final:
            raise erro_final
        raise RuntimeError("ANP indisponivel (nenhum arquivo encontrado)")

    def collect(self):
        conteudo = self._baixar()
        return parse_precos(conteudo), parse_precos_uf(conteudo)

    def run(self):
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
        except Exception as exc:
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        log_run(result)
        return result
