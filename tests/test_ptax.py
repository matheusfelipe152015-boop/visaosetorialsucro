"""Testa o parse do coletor BCB PTAX sem rede (payload de exemplo)."""

from datetime import date

from src.collectors.market.bcb_ptax import parse_sgs

SAMPLE = [
    {"data": "19/06/2026", "valor": "5.3980"},
    {"data": "20/06/2026", "valor": "5.4127"},
]


def test_parse_basic():
    values = parse_sgs(SAMPLE)
    assert len(values) == 2
    v = values[1]
    assert v.data_referencia == date(2026, 6, 20)
    assert v.valor == 5.4127
    assert v.unidade == "BRL/USD"
    assert v.indicator_code == "usd_brl"
    assert v.source_code == "bcb_sgs"


def test_hash_is_deterministic():
    a = parse_sgs(SAMPLE)[0].hash
    b = parse_sgs(SAMPLE)[0].hash
    assert a == b and len(a) == 16
