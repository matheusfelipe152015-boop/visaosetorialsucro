"""Testa o parser das cotações internacionais (offline, formato real do Yahoo)."""

from datetime import date

from src.collectors.market.cotacoes_intl import parse_yahoo

# Formato real do Yahoo Finance (recortado)
PAYLOAD = {
    "chart": {
        "result": [
            {
                "meta": {"symbol": "SB=F"},
                "timestamp": [1751328000, 1751414400, 1751500800],
                "indicators": {
                    "quote": [{"close": [14.83, 14.91, None]}]  # None = pregão sem fecho
                },
            }
        ]
    }
}


def test_extrai_fechamentos():
    vals = parse_yahoo(PAYLOAD, "SB=F")
    assert len(vals) == 2  # o None foi descartado
    assert vals[0].indicator_code == "sugar_ny11"
    assert vals[0].valor == 14.83
    assert vals[0].unidade == "¢/lb"
    assert vals[1].valor == 14.91


def test_marca_como_fonte_a_conferir():
    """A fonte primária (ICE) é paga; o Yahoo é secundário -> sinalizado."""
    v = parse_yahoo(PAYLOAD, "SB=F")[0]
    assert v.status_validacao.value == "pending"  # fonte secundária
    assert v.source_code == "yahoo"


def test_data_de_referencia_correta():
    v = parse_yahoo(PAYLOAD, "SB=F")[0]
    assert isinstance(v.data_referencia, date)


def test_ticker_desconhecido_e_ignorado():
    assert parse_yahoo(PAYLOAD, "XX=F") == []


def test_payload_vazio_nao_quebra():
    assert parse_yahoo({}, "SB=F") == []
    assert parse_yahoo({"chart": {"result": []}}, "SB=F") == []
