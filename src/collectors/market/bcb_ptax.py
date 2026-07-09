"""Coletor BCB — câmbio USD/BRL (PTAX venda).

Fonte: Banco Central do Brasil, Sistema Gerenciador de Séries Temporais (SGS),
série 1 = "Taxa de câmbio - Livre - Dólar americano (venda) - diário".
API pública, formato JSON, sem autenticação e com histórico longo.

Endpoint:
  https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados?formato=json
  &dataInicial=dd/mm/aaaa&dataFinal=dd/mm/aaaa

O parse é separado do fetch para ser testável offline (ver tests/test_ptax.py).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx

from src.collectors.base import Collector
from src.domain.enums import ValidationStatus
from src.domain.models import IndicatorValue

BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
SERIE_USD_VENDA = 1
SOURCE_CODE = "bcb_sgs"
INDICATOR_CODE = "usd_brl"


def parse_sgs(payload: list[dict]) -> list[IndicatorValue]:
    """Converte a resposta crua do SGS em IndicatorValue normalizados.

    Cada item vem como {"data": "dd/mm/aaaa", "valor": "5.1234"}.
    """
    out: list[IndicatorValue] = []
    for row in payload:
        ref = datetime.strptime(row["data"], "%d/%m/%Y").date()
        out.append(
            IndicatorValue(
                indicator_code=INDICATOR_CODE,
                source_code=SOURCE_CODE,
                data_referencia=ref,
                valor=float(row["valor"]),
                unidade="BRL/USD",
                moeda="BRL",
                escala="unit",
                data_publicacao=ref,
                collector_version="0.1.0",
                status_validacao=ValidationStatus.OK,
                url_original=BCB_URL.format(serie=SERIE_USD_VENDA),
            )
        )
    return out


class BcbPtaxCollector(Collector):
    source_code = SOURCE_CODE
    version = "0.1.0"

    def __init__(self, days: int = 1825) -> None:  # ~5 anos por padrão
        self.days = days

    def collect(self) -> list[IndicatorValue]:
        end = date.today()
        start = end - timedelta(days=self.days)
        params = {
            "formato": "json",
            "dataInicial": start.strftime("%d/%m/%Y"),
            "dataFinal": end.strftime("%d/%m/%Y"),
        }
        url = BCB_URL.format(serie=SERIE_USD_VENDA)
        resp = httpx.get(
            url,
            params=params,
            timeout=30,
            headers={"User-Agent": "canavis/0.1 (intel-sucroenergetico)"},
        )
        resp.raise_for_status()
        return parse_sgs(resp.json())
