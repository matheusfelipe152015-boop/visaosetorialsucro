"""Testa o parser do coletor de indicadores macro do BCB."""

from datetime import date

from src.collectors.market.bcb_macro import parse_sgs_serie

SAMPLE = [
    {"data": "01/05/2026", "valor": "10.75"},
    {"data": "01/06/2026", "valor": "10.50"},
]


def test_parse_serie_basico():
    vals = parse_sgs_serie(SAMPLE, "selic_meta", "% a.a.")
    assert len(vals) == 2
    assert vals[0].indicator_code == "selic_meta"
    assert vals[0].valor == 10.75
    assert vals[0].data_referencia == date(2026, 5, 1)
    assert vals[0].unidade == "% a.a."


def test_parse_aceita_virgula():
    vals = parse_sgs_serie([{"data": "01/06/2026", "valor": "5,25"}], "cdi_diario", "% a.d.")
    assert vals[0].valor == 5.25


def test_parse_vazio():
    assert parse_sgs_serie([], "ipca_mensal", "% mês") == []
