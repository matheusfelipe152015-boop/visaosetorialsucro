"""Testa o parser do Comex Stat, offline (resposta de exemplo)."""

from datetime import date

from src.collectors.market.comex_export import parse_resposta

# Resposta no formato da API: data.list com registros por NCM e mês.
SAMPLE = {
    "data": {
        "list": [
            # açúcar (dois NCMs no mesmo mês -> somam)
            {"coNcm": "17011400", "year": 2026, "monthNumber": 5, "metricFOB": "1000", "metricKG": "10"},
            {"coNcm": "17019900", "year": 2026, "monthNumber": 5, "metricFOB": "500", "metricKG": "5"},
            # etanol no mesmo mês
            {"coNcm": "22071000", "year": 2026, "monthNumber": 5, "metricFOB": "300", "metricKG": "3"},
            # açúcar em outro mês
            {"coNcm": "17011400", "year": 2026, "monthNumber": 4, "metricFOB": "800", "metricKG": "8"},
            # NCM fora do escopo -> ignorado
            {"coNcm": "09011100", "year": 2026, "monthNumber": 5, "metricFOB": "999", "metricKG": "9"},
        ]
    }
}


def _idx(values):
    return {(v.indicator_code, v.data_referencia): v for v in values}


def test_soma_acucar_por_mes():
    by = _idx(parse_resposta(SAMPLE))
    assert by[("exp_acucar", date(2026, 5, 1))].valor == 1500.0  # 1000 + 500
    assert by[("exp_acucar", date(2026, 4, 1))].valor == 800.0


def test_etanol_separado_do_acucar():
    by = _idx(parse_resposta(SAMPLE))
    assert by[("exp_etanol", date(2026, 5, 1))].valor == 300.0
    assert ("exp_etanol", date(2026, 4, 1)) not in by


def test_ignora_ncm_fora_do_escopo():
    vals = parse_resposta(SAMPLE)
    # café (09011100) não pode virar indicador
    total_registros = len(vals)
    assert total_registros == 3  # açúcar mai, açúcar abr, etanol mai


def test_metadados():
    v = _idx(parse_resposta(SAMPLE))[("exp_acucar", date(2026, 5, 1))]
    assert v.unidade == "US$ FOB"
    assert v.moeda == "USD"
    assert v.source_code == "comex"
