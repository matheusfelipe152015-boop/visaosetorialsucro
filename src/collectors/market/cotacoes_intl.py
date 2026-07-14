"""Coletor de cotacoes internacionais (acucar NY no 11, Brent).

Fonte: Yahoo Finance (endpoint publico, sem cadastro).

HONESTIDADE SOBRE A FONTE:
  - A fonte PRIMARIA do acucar NY no 11 e a bolsa ICE, e o dado oficial e PAGO.
    O Yahoo republica a cotacao com atraso.
  - Serve para LER TENDENCIA, nao para liquidar contrato.
  - E API nao-oficial: se o Yahoo mudar, o coletor FALHA (aparece em Saude dos
    dados) — mas nunca inventa numero.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from src.collectors.base import Collector
from src.domain.enums import ValidationStatus
from src.domain.models import IndicatorValue

SOURCE_CODE = "yahoo"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

TICKERS = {
    "SB=F": ("sugar_ny11", "\u00a2/lb", "USD"),
    "BZ=F": ("brent", "US$/bbl", "USD"),
}


def parse_yahoo(payload, ticker):
    """Extrai os fechamentos diarios do JSON do Yahoo."""
    if ticker not in TICKERS:
        return []
    code, unidade, moeda = TICKERS[ticker]

    resultado = (payload.get("chart") or {}).get("result") or []
    if not resultado:
        return []
    r = resultado[0]
    timestamps = r.get("timestamp") or []
    quotes = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quotes.get("close") or []

    agora = datetime.now(timezone.utc)
    out = []
    for ts, close in zip(timestamps, closes, strict=False):
        if close is None:
            continue
        ref = datetime.fromtimestamp(ts, tz=timezone.utc).date()
        out.append(
            IndicatorValue(
                indicator_code=code,
                source_code=SOURCE_CODE,
                data_referencia=ref,
                valor=round(float(close), 4),
                unidade=unidade,
                moeda=moeda,
                escala="unit",
                data_publicacao=ref,
                data_coleta=agora.replace(tzinfo=None),
                collector_version="0.1.0",
                status_validacao=ValidationStatus.PENDING,
                url_original=f"https://finance.yahoo.com/quote/{ticker}",
            )
        )
    return out


class CotacoesIntlCollector(Collector):
    source_code = SOURCE_CODE
    version = "0.1.0"

    def __init__(self, range_="3mo"):
        self.range = range_

    def collect(self):
        out = []
        for ticker in TICKERS:
            try:
                resp = httpx.get(
                    YAHOO_URL.format(ticker=ticker),
                    params={"range": self.range, "interval": "1d"},
                    timeout=30,
                    follow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; visaosetorialsucro/0.1)"},
                )
                resp.raise_for_status()
                out.extend(parse_yahoo(resp.json(), ticker))
            except Exception:
                continue
        return out
