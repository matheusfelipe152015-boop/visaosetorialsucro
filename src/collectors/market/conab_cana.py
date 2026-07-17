"""Coletor CONAB — safra de cana (produção, área, ATR) por estado e Brasil.

Fonte: Portal de Informações Agropecuárias da CONAB (dados abertos).
Arquivo: SerieHistoricaCana.txt — CSV ';', uma linha por UF × safra.

Guarda DOIS níveis:
  1. por estado  -> tabela safra_uf (alimenta o mapa do Brasil);
  2. total Brasil -> indicator_values (alimenta os KPIs/indicadores).

O ATR é média ponderada pela produção (somar ATR não faria sentido).

Licença: a CONAB autoriza reprodução sem fins lucrativos, citando a fonte.
Números: a área usa VÍRGULA decimal ("402,1"); a produção usa PONTO ("23110.7").
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime

import httpx
from sqlalchemy import text

from src.domain.enums import ValidationStatus
from src.domain.models import CollectorResult, IndicatorValue
from src.persistence.db import get_engine
from src.persistence.repositories import log_run, upsert_indicator_values
from src.services.chuva import REGIAO_POR_UF

CONAB_URL = "https://portaldeinformacoes.conab.gov.br/downloads/arquivos/SerieHistoricaCana.txt"
SOURCE_CODE = "conab"

COLUNAS = {
    "area_plantada_mil_ha": ("cana_area_plantada", "mil ha"),
    "producao_mil_t": ("cana_producao", "mil t"),
    "producao_acucar_mil_t": ("acucar_producao", "mil t"),
    "producao_etanol_total_mil_l": ("etanol_producao", "mil L"),
}
COL_ATR = "produtcao_atr_kg_t"  # (sic: o nome vem com typo no arquivo da CONAB)


def _num(v):
    s = (v or "").strip()
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _data_da_safra(ano_agricola):
    """Safra '2025/26' -> 31/03/2026 (fim do ciclo)."""
    s = (ano_agricola or "").strip()
    if "/" not in s:
        return None
    ini, fim = s.split("/", 1)
    try:
        ano_ini = int(ini)
        ano_fim = int(str(ano_ini)[:2] + fim.zfill(2))
        if ano_fim < ano_ini:
            ano_fim += 100
        return date(ano_fim, 3, 31)
    except ValueError:
        return None


def parse_conab_uf(conteudo: str) -> list[dict]:
    """Extrai as linhas por ESTADO (para o mapa)."""
    out: list[dict] = []
    for linha in csv.DictReader(io.StringIO(conteudo), delimiter=";"):
        safra = (linha.get("ano_agricola") or "").strip()
        uf = (linha.get("uf") or "").strip()
        if not safra or not uf:
            continue
        ref = _data_da_safra(safra)
        for coluna, (code, unidade) in COLUNAS.items():
            val = _num(linha.get(coluna, ""))
            if val is None:
                continue
            out.append({
                "uf": uf, "regiao": REGIAO_POR_UF.get(uf), "safra": safra,
                "metric": code, "valor": val, "unidade": unidade,
                "data_referencia": ref,
            })
        atr = _num(linha.get(COL_ATR, ""))
        if atr is not None:
            out.append({
                "uf": uf, "regiao": REGIAO_POR_UF.get(uf), "safra": safra,
                "metric": "cana_atr_medio", "valor": atr, "unidade": "kg/t",
                "data_referencia": ref,
            })
    return out


def agrega_brasil(linhas_uf: list[dict]) -> list[IndicatorValue]:
    """Soma os estados no total Brasil (ATR = média ponderada pela produção)."""
    somas: dict[tuple, float] = {}
    prod_por_uf_safra: dict[tuple, float] = {}
    atr_pares: dict[str, list] = {}

    for r in linhas_uf:
        if r["metric"] == "cana_producao":
            prod_por_uf_safra[(r["uf"], r["safra"])] = r["valor"]

    for r in linhas_uf:
        if r["metric"] == "cana_atr_medio":
            peso = prod_por_uf_safra.get((r["uf"], r["safra"]), 0.0)
            if peso:
                atr_pares.setdefault(r["safra"], []).append((r["valor"], peso))
        else:
            chave = (r["safra"], r["metric"], r["unidade"], r["data_referencia"])
            somas[chave] = somas.get(chave, 0.0) + r["valor"]

    agora = datetime.utcnow()
    out: list[IndicatorValue] = []
    for (_safra, metric, unidade, ref), total in somas.items():
        if ref is None:
            continue
        out.append(IndicatorValue(
            indicator_code=metric, source_code=SOURCE_CODE, data_referencia=ref,
            valor=round(total, 2), unidade=unidade, escala="unit",
            data_publicacao=ref, data_coleta=agora, collector_version="0.1.0",
            status_validacao=ValidationStatus.OK, url_original=CONAB_URL,
        ))
    for safra, pares in atr_pares.items():
        ref = _data_da_safra(safra)
        peso_total = sum(p for _a, p in pares)
        if not peso_total or ref is None:
            continue
        media = sum(a * p for a, p in pares) / peso_total
        out.append(IndicatorValue(
            indicator_code="cana_atr_medio", source_code=SOURCE_CODE, data_referencia=ref,
            valor=round(media, 1), unidade="kg/t", escala="unit",
            data_publicacao=ref, data_coleta=agora, collector_version="0.1.0",
            status_validacao=ValidationStatus.OK, url_original=CONAB_URL,
        ))
    return out


def upsert_safra_uf(linhas: list[dict]) -> int:
    """Grava as linhas por estado (idempotente)."""
    eng = get_engine()
    agora = datetime.utcnow()
    novos = 0
    with eng.begin() as conn:
        for r in linhas:
            existe = conn.execute(
                text("SELECT 1 FROM safra_uf WHERE uf=:u AND safra=:s "
                     "AND metric=:m AND source_code=:src"),
                {"u": r["uf"], "s": r["safra"], "m": r["metric"], "src": SOURCE_CODE},
            ).first()
            if not existe:
                novos += 1
            conn.execute(
                text("""INSERT INTO safra_uf(id,uf,regiao,safra,metric,valor,unidade,
                          data_referencia,source_code,data_coleta,collector_version,url_original)
                        VALUES(:id,:u,:rg,:s,:m,:v,:un,:dr,:src,:dc,:cv,:url)
                        ON CONFLICT(uf,safra,metric,source_code) DO UPDATE SET
                          valor=excluded.valor, data_coleta=excluded.data_coleta"""),
                {"id": uuid.uuid4().hex, "u": r["uf"], "rg": r["regiao"], "s": r["safra"],
                 "m": r["metric"], "v": r["valor"], "un": r["unidade"],
                 "dr": r["data_referencia"], "src": SOURCE_CODE, "dc": agora,
                 "cv": "0.1.0", "url": CONAB_URL},
            )
    return novos


class ConabCanaCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def collect(self) -> tuple[list[dict], list[IndicatorValue]]:
        resp = httpx.get(CONAB_URL, timeout=60, headers={"User-Agent": "visaosetorialsucro/0.1"})
        resp.raise_for_status()
        texto = resp.content.decode("utf-8", errors="replace")
        por_uf = parse_conab_uf(texto)
        brasil = agrega_brasil(por_uf)
        return por_uf, brasil

    def run(self) -> CollectorResult:
        started = datetime.utcnow()
        try:
            por_uf, brasil = self.collect()
            n1 = upsert_safra_uf(por_uf)
            n2 = upsert_indicator_values(brasil)
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(),
                rows_seen=len(por_uf) + len(brasil), rows_new=n1 + n2, ok=True,
            )
        except Exception as exc:  # noqa: BLE001
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        log_run(result)
        return result
