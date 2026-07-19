"""Coletor de cotações internacionais (açúcar NY nº 11, Brent).

Fonte: Yahoo Finance (endpoint público de gráficos, sem cadastro).

HONESTIDADE SOBRE A FONTE — leia antes de usar em decisão:
  · A fonte PRIMÁRIA do açúcar NY nº 11 é a bolsa ICE, e o dado oficial dela é
    pago. O Yahoo republica a cotação com atraso.
  · Portanto, este número serve para LER TENDÊNCIA de mercado, não para
    liquidar contrato. Para uso contratual, assine a ICE.
  · É uma API não-oficial: o Yahoo pode mudá-la sem aviso. Se isso acontecer,
    o coletor falha (e aparece em "Saúde dos dados") — mas não inventa número.

Por isso os valores entram com status "a_conferir": a plataforma mostra, mas
avisa que é fonte secundária.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from src.collectors.base import Collector
from src.domain.enums import ValidationStatus
from src.domain.models import IndicatorValue

SOURCE_CODE = "yahoo"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

# ticker do Yahoo -> (indicador na plataforma, unidade, moeda)
TICKERS = {
    "SB=F": ("sugar_ny11", "¢/lb", "USD"),   # Açúcar NY nº 11 (ICE)
    "BZ=F": ("brent", "US$/bbl", "USD"),     # Petróleo Brent
}


def parse_yahoo(payload: dict, ticker: str) -> list[IndicatorValue]:
    """Extrai os fechamentos diários do JSON do Yahoo."""
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

    agora = datetime.now(UTC)
    out: list[IndicatorValue] = []
    for ts, close in zip(timestamps, closes, strict=False):
        if close is None:
            continue  # feriado/pregão sem fechamento
        ref = datetime.fromtimestamp(ts, tz=UTC).date()
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
                # fonte secundária (a primária, ICE, é paga): sinalizamos
                status_validacao=ValidationStatus.PENDING,
                url_original=f"https://finance.yahoo.com/quote/{ticker}",
            )
        )
    return out


class CotacoesIntlCollector(Collector):
    source_code = SOURCE_CODE
    version = "0.1.0"

    def __init__(self, range_: str = "3mo") -> None:
        self.range = range_

    def collect(self) -> list[IndicatorValue]:
        out: list[IndicatorValue] = []
        # User-Agent de navegador real: o Yahoo bloqueia agentes "não-browser"
        # quando a requisição vem de IP de datacenter (ex.: GitHub Actions).
        headers = {
            "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/126.0.0.0 Safari/537.36"),
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        # tenta os dois hosts do Yahoo (query1 e query2) com algumas tentativas
        hosts = ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]
        for ticker in TICKERS:
            valores: list[IndicatorValue] = []
            for tentativa in range(3):
                host = hosts[tentativa % len(hosts)]
                url = f"https://{host}/v8/finance/chart/{ticker}"
                try:
                    resp = httpx.get(
                        url,
                        params={"range": self.range, "interval": "1d"},
                        timeout=30, follow_redirects=True, headers=headers,
                    )
                    resp.raise_for_status()
                    valores = parse_yahoo(resp.json(), ticker)
                    if valores:
                        break
                except Exception:  # noqa: BLE001 — tenta o próximo host/tentativa
                    continue
            out.extend(valores)
        return out
