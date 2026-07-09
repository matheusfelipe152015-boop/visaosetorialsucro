"""Testa o motor de extração por palavras-chave."""

from src.services.release_reader import extrair_metric, ler_release

# Trechos no estilo de releases reais (texto corrido).
TEXTO_SM = (
    "No 3T26, a moagem de cana atingiu 24,1 milhões de toneladas, alta de 3,9%. "
    "O mix de açúcar foi de 51%, enquanto o ATR alcançou 138,5 kg/t. "
    "A produção de açúcar somou 1.320 mil ton e a receita líquida foi de R$ 1.850 milhões. "
    "O EBITDA ajustado totalizou R$ 720 milhões no período."
)


def test_extrai_moagem():
    e = extrair_metric(TEXTO_SM, "moagem")
    assert e.valor == 24.1
    assert e.unidade == "Mt"
    assert e.confiabilidade == "a_conferir"  # regra de ouro


def test_extrai_atr():
    e = extrair_metric(TEXTO_SM, "atr")
    assert e.valor == 138.5
    assert e.unidade == "kg/t"


def test_extrai_mix_acucar():
    e = extrair_metric(TEXTO_SM, "mix_acucar")
    assert e.valor == 51.0


def test_extrai_producao_acucar_formato_br():
    # 1.320 mil ton -> ponto é separador de milhar -> 1320
    e = extrair_metric(TEXTO_SM, "prod_acucar")
    assert e.valor == 1320.0


def test_extrai_receita():
    e = extrair_metric(TEXTO_SM, "receita")
    assert e.valor == 1850.0


def test_nao_inventa_quando_ausente():
    # texto sem menção a etanol -> não pode retornar valor
    e = extrair_metric("Texto sem dados de etanol aqui.", "prod_etanol")
    assert e.valor is None
    assert e.rotulo_encontrado is None


def test_guarda_evidencia():
    e = extrair_metric(TEXTO_SM, "moagem")
    assert e.evidencia is not None
    assert "moagem" in e.evidencia.lower()


def test_ler_release_conta_encontrados():
    res = ler_release(TEXTO_SM, "sao_martinho")
    # deve encontrar moagem, mix_acucar, atr, prod_acucar, receita, ebitda (6+)
    assert res.encontrados >= 5
    assert res.company_code == "sao_martinho"
