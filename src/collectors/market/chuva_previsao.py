"""Coletor de previsão de chuva 14 dias — polos canavieiros e portos.

Fonte: CSV aberto do projeto sugar-intel (dados de previsão do Open-Meteo),
redistribuído em https://strongylis.github.io/sugar-intel/data/chuva_14d.csv

Complementa a chuva OBSERVADA (INMET, tabela rainfall): aqui é a PREVISÃO diária
por cidade para os próximos 14 dias, útil para antecipar risco de safra.

Atribuição: previsão Open-Meteo, compilada por sugar-intel (Igor Strongylis).
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime

import httpx
from sqlalchemy import text

from src.domain.models import CollectorResult
from src.persistence.db import get_engine
from src.persistence.repositories import log_run

SOURCE_CODE = "sugar_intel"
CSV_URL = "https://strongylis.github.io/sugar-intel/data/chuva_14d.csv"

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
}


def _num(v):
    s = (v or "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_chuva(texto: str) -> list[dict]:
    """Lê o CSV e devolve linhas prontas para gravar."""
    linhas = []
    leitor = csv.DictReader(io.StringIO(texto))
    for r in leitor:
        cidade = (r.get("cidade") or "").strip()
        dprev = (r.get("data_prev") or "").strip()
        precip = _num(r.get("precip_mm"))
        if not cidade or not dprev or precip is None:
            continue
        try:
            data_prev = date.fromisoformat(dprev[:10])
        except ValueError:
            continue
        coleta = (r.get("data_coleta") or "").strip()
        try:
            data_coleta = date.fromisoformat(coleta[:10]) if coleta else date.today()
        except ValueError:
            data_coleta = date.today()
        linhas.append({
            "cidade": cidade, "data_prev": data_prev, "precip_mm": precip,
            "lat": _num(r.get("lat")), "lon": _num(r.get("lon")),
            "data_coleta": data_coleta, "fonte_url": (r.get("fonte_url") or "").strip(),
        })
    return linhas


def _upsert(linhas: list[dict]) -> int:
    novos = 0
    with get_engine().begin() as conn:
        for x in linhas:
            existe = conn.execute(
                text("SELECT id FROM chuva_previsao WHERE cidade=:c AND data_prev=:d"),
                {"c": x["cidade"], "d": x["data_prev"]},
            ).first()
            params = {**x, "id": uuid.uuid4().hex}
            if existe:
                conn.execute(
                    text("""UPDATE chuva_previsao SET precip_mm=:precip_mm, lat=:lat,
                            lon=:lon, data_coleta=:data_coleta, fonte_url=:fonte_url
                            WHERE cidade=:cidade AND data_prev=:data_prev"""), params)
            else:
                conn.execute(
                    text("""INSERT INTO chuva_previsao
                            (id,cidade,data_prev,precip_mm,lat,lon,data_coleta,fonte_url)
                            VALUES(:id,:cidade,:data_prev,:precip_mm,:lat,:lon,
                                   :data_coleta,:fonte_url)"""), params)
                novos += 1
    return novos


class ChuvaPrevisaoCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def collect(self) -> list[dict]:
        resp = httpx.get(CSV_URL, timeout=60, follow_redirects=True, headers=_HEADERS)
        resp.raise_for_status()
        return parse_chuva(resp.content.decode("utf-8", errors="replace"))

    def run(self) -> CollectorResult:
        started = datetime.utcnow()
        try:
            linhas = self.collect()
            n = _upsert(linhas)
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), rows_seen=len(linhas),
                rows_new=n, ok=True,
            )
        except Exception as exc:  # noqa: BLE001
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        log_run(result)
        return result
