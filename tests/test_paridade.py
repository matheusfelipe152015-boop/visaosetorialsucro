"""Testa o cálculo de paridade etanol/gasolina."""

from src.services.paridade import etanol_compensa, leitura_paridade, paridade


def test_paridade_basica():
    # etanol 4,20 / gasolina 6,00 = 0,70 (comparação com tolerância p/ decimais)
    assert abs(paridade(4.20, 6.00) - 0.70) < 1e-9


def test_etanol_compensa_abaixo_de_70():
    # 4,02 / 6,00 = 0,67 -> compensa
    assert etanol_compensa(4.02, 6.00) is True


def test_gasolina_compensa_acima_de_70():
    # 4,50 / 6,00 = 0,75 -> não compensa
    assert etanol_compensa(4.50, 6.00) is False


def test_gasolina_zero_nao_quebra():
    assert paridade(4.0, 0) is None
    assert etanol_compensa(4.0, 0) is None
    assert leitura_paridade(4.0, 0) == "—"


def test_leitura_texto():
    assert "etanol compensa" in leitura_paridade(4.02, 6.00)
    assert "gasolina compensa" in leitura_paridade(4.50, 6.00)
