"""Testa o parser do CBIO (offline, formato da B3)."""

from datetime import date

from src.collectors.market.cbio_b3 import _num, parse_cbio

# Amostra no formato da B3 (nomes de coluna em camelCase)
PAYLOAD = {
    "Trades": [
        {"price": "30,0000000", "quantity": "5.000"},
        {"price": "29,8000000", "quantity": "1.816"},
        {"price": "30,5000000", "quantity": "600"},
    ]
}


def test_num_formato_br():
    assert _num("30,0000000") == 30.0
    assert _num("29,80") == 29.8
    assert _num("5.000") == 5000.0   # ponto de milhar
    assert _num("") is None


def test_media_ponderada_pela_quantidade():
    iv = parse_cbio(PAYLOAD, date(2026, 7, 13))
    assert iv is not None
    assert iv.indicator_code == "cbio"
    # média ponderada: (30*5000 + 29,8*1816 + 30,5*600) / (5000+1816+600)
    esperado = (30.0 * 5000 + 29.8 * 1816 + 30.5 * 600) / (5000 + 1816 + 600)
    assert abs(iv.valor - round(esperado, 2)) < 0.01
    # fica entre o menor e o maior preço (sanidade)
    assert 29.8 <= iv.valor <= 30.5


def test_unidade_e_fonte():
    iv = parse_cbio(PAYLOAD, date(2026, 7, 13))
    assert iv.unidade == "R$/un"
    assert iv.source_code == "b3"


def test_sem_negocios_nao_grava():
    assert parse_cbio({"Trades": []}, date(2026, 7, 13)) is None
    assert parse_cbio({}, date(2026, 7, 13)) is None


def test_aceita_nomes_de_coluna_alternativos():
    p = {"dados": [{"PrecoDoNegocio": "31,00", "QtdNegociada": "100"}]}
    iv = parse_cbio(p, date(2026, 7, 13))
    assert iv is not None
    assert iv.valor == 31.0
