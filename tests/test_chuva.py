"""Testa a agregação de chuva por região e o cálculo de anomalia."""

from src.services.chuva import (
    anomalia,
    chuva_por_regiao,
    classifica_anomalia,
    regiao_da_uf,
)


def test_regiao_da_uf():
    assert regiao_da_uf("SP") == "Sudeste"
    assert regiao_da_uf("ba") == "Nordeste"  # aceita minúscula
    assert regiao_da_uf("XX") is None


def test_chuva_por_regiao_media():
    por_uf = {"SP": 100.0, "MG": 140.0, "RS": 80.0}  # Sudeste: SP, MG | Sul: RS
    reg = chuva_por_regiao(por_uf)
    assert reg["Sudeste"] == 120.0  # média de 100 e 140
    assert reg["Sul"] == 80.0
    assert "Norte" not in reg  # sem dados -> não aparece


def test_anomalia():
    assert anomalia(120, 100) == 20.0
    assert anomalia(80, 100) == -20.0
    assert anomalia(100, 0) is None  # evita divisão por zero


def test_classifica_anomalia():
    assert classifica_anomalia(25) == "muito acima do normal"
    assert classifica_anomalia(10) == "acima do normal"
    assert classifica_anomalia(0) == "dentro do normal"
    assert classifica_anomalia(-10) == "abaixo do normal"
    assert classifica_anomalia(-30) == "muito abaixo do normal"
    assert classifica_anomalia(None) == "sem referência"
