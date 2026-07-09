"""Coletor Comex Stat (MDIC) — exportações de açúcar e etanol.

Fonte: API oficial do Comex Stat (estatísticas de comércio exterior do Brasil).
Licença Creative Commons (atribuição). A consulta é um POST em /general pedindo
o fluxo de exportação, por mês, filtrado pelos NCM de açúcar e etanol, com as
métricas de valor (US$ FOB) e peso (kg).

Geramos, por mês:
  - exp_acucar  : valor exportado de açúcar (US$ FOB)
  - exp_etanol  : valor exportado de etanol (US$ FOB)

O parse (parse_resposta) é separado da chamada de rede para ser testável offline
(ver tests/test_comex.py). O ambiente de desenvolvimento não acessa a internet;
a coleta real roda na máquina do usuário / no agendador.
"""

from __future__ import annotations

from datetime import date, datetime

import httpx

from src.collectors.base import Collector
from src.domain.enums import ValidationStatus
from src.domain.models import IndicatorValue

SOURCE_CODE = "comex"
API_URL = "https://api-comexstat.mdic.gov.br/general?language=pt"

# NCM (Nomenclatura Comum do Mercosul) por grupo de produto.
NCM_ACUCAR = ["17011400", "17011300", "17019100", "17019900"]  # bruto/VHP e refinado
NCM_ETANOL = ["22071000", "22072000"]  # etanol não desnaturado e desnaturado

# Mapa de qual indicador recebe cada NCM.
_GRUPO = {ncm: "exp_acucar" for ncm in NCM_ACUCAR}
_GRUPO.update({ncm: "exp_etanol" for ncm in NCM_ETANOL})

_NOME = {"exp_acucar": "Exportações de açúcar", "exp_etanol": "Exportações de etanol"}


def parse_resposta(payload: dict) -> list[IndicatorValue]:
    """Converte a resposta JSON do Comex Stat em valores mensais por grupo.

    A API devolve uma lista de registros em payload['data']['list'], cada um com
    ano, mês, NCM (coNcm) e as métricas. Aqui somamos o valor FOB por grupo
    (açúcar/etanol) e por mês de referência.
    """
    registros = payload.get("data", {}).get("list", []) or []
    # acumula valor FOB por (indicador, ano, mes)
    acumulado: dict[tuple[str, int, int], float] = {}
    for r in registros:
        ncm = str(r.get("coNcm", "")).zfill(8)
        grupo = _GRUPO.get(ncm)
        if grupo is None:
            continue
        ano = int(r.get("year") or r.get("coYear") or r.get("ano"))
        mes = int(r.get("monthNumber") or r.get("coMonth") or r.get("mes") or 1)
        fob = float(str(r.get("metricFOB", 0)).replace(",", ".") or 0)
        acumulado[(grupo, ano, mes)] = acumulado.get((grupo, ano, mes), 0.0) + fob

    out: list[IndicatorValue] = []
    for (grupo, ano, mes), fob in sorted(acumulado.items()):
        # data de referência = último dia conceitual do mês (usamos o dia 1)
        ref = date(ano, mes, 1)
        out.append(
            IndicatorValue(
                indicator_code=grupo,
                source_code=SOURCE_CODE,
                data_referencia=ref,
                valor=round(fob, 2),
                unidade="US$ FOB",
                moeda="USD",
                escala="unit",
                data_publicacao=ref,
                data_coleta=datetime.utcnow(),
                collector_version="0.1.0",
                status_validacao=ValidationStatus.OK,
                url_original="https://comexstat.mdic.gov.br/",
            )
        )
    return out


class ComexExportCollector(Collector):
    source_code = SOURCE_CODE
    version = "0.1.0"

    def __init__(self, meses: int = 24) -> None:
        self.meses = meses

    def _periodo(self) -> tuple[str, str]:
        hoje = date.today()
        # de N meses atrás até o mês anterior (o mês corrente costuma estar incompleto)
        fim_ano, fim_mes = hoje.year, hoje.month
        ini = fim_ano * 12 + (fim_mes - 1) - self.meses
        ini_ano, ini_mes = divmod(ini, 12)
        return f"{ini_ano:04d}-{ini_mes + 1:02d}", f"{fim_ano:04d}-{fim_mes:02d}"

    def collect(self) -> list[IndicatorValue]:
        desde, ate = self._periodo()
        body = {
            "flow": "export",
            "monthDetail": True,
            "period": {"from": desde, "to": ate},
            "filters": [{"filter": "ncm", "values": NCM_ACUCAR + NCM_ETANOL}],
            "details": ["ncm"],
            "metrics": ["metricFOB", "metricKG"],
        }
        resp = httpx.post(
            API_URL,
            json=body,
            timeout=120,
            headers={"User-Agent": "canavis/0.1 (intel-sucroenergetico)"},
        )
        resp.raise_for_status()
        return parse_resposta(resp.json())
