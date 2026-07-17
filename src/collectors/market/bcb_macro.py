"""Coletor BCB — indicadores macroeconômicos (Selic, IPCA, IGP-M, CDI).

Cada série é buscada de forma independente e resiliente: se uma falhar (ex.:
servidor lento), as demais ainda são coletadas. Timeout generoso (60s).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx

from src.collectors.base import Collector
from src.domain.enums import ValidationStatus
from src.domain.models import IndicatorValue

BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados"
SOURCE_CODE = "bcb_sgs"

SERIES: dict[str, tuple[int, str]] = {
    "selic_meta": (432, "% a.a."),
    "ipca_mensal": (433, "% mes"),
    "igpm_mensal": (189, "% mes"),
    "cdi_diario": (12, "% a.d."),
}


def parse_sgs_serie(payload, indicator_code, unidade):
    out = []
    for row in payload:
        ref = datetime.strptime(row["data"], "%d/%m/%Y").date()
        out.append(
            IndicatorValue(
                indicator_code=indicator_code,
                source_code=SOURCE_CODE,
                data_referencia=ref,
                valor=float(str(row["valor"]).replace(",", ".")),
                unidade=unidade,
                escala="unit",
                data_publicacao=ref,
                collector_version="0.1.0",
                status_validacao=ValidationStatus.OK,
                url_original="https://dadosabertos.bcb.gov.br/",
            )
        )
    return out


class BcbMacroCollector(Collector):
    source_code = SOURCE_CODE
    version = "0.1.0"

    def __init__(self, days: int = 365) -> None:
        self.days = days

    def collect(self):
        end = date.today()
        start = end - timedelta(days=self.days)
        params = {
            "formato": "json",
            "dataInicial": start.strftime("%d/%m/%Y"),
            "dataFinal": end.strftime("%d/%m/%Y"),
        }
        todos = []
        for code, (serie, unidade) in SERIES.items():
            try:
                resp = httpx.get(
                    BCB_URL.format(serie=serie),
                    params=params,
                    timeout=60,
                    headers={"User-Agent": "visaosetorialsucro/0.1"},
                )
                resp.raise_for_status()
                todos.extend(parse_sgs_serie(resp.json(), code, unidade))
            except Exception as exc:  # noqa: BLE001 — uma série lenta não derruba as outras
                print(f"  (aviso: série {code} falhou: {type(exc).__name__})")
        return todos
