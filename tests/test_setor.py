"""Testa a leitura agregada do setor (dados das empresas)."""

from src.services.setor import mix_medio, soma_metric, tendencia, variacao_pct

REGISTROS = [
    {"company": "sao_martinho", "metric": "moagem", "valor": 24.0, "periodo": "3T26"},
    {"company": "raizen", "metric": "moagem", "valor": 80.0, "periodo": "3T26"},
    {"company": "jalles", "metric": "moagem", "valor": 4.5, "periodo": "3T26"},
    {"company": "sao_martinho", "metric": "moagem", "valor": 23.0, "periodo": "3T25"},
    {"company": "raizen", "metric": "moagem", "valor": 78.0, "periodo": "3T25"},
    {"company": "jalles", "metric": "moagem", "valor": 4.4, "periodo": "3T25"},
    {"company": "sao_martinho", "metric": "mix_acucar", "valor": 51.0, "periodo": "3T26"},
    {"company": "raizen", "metric": "mix_acucar", "valor": 47.0, "periodo": "3T26"},
    {"company": "sao_martinho", "metric": "mix_etanol", "valor": 49.0, "periodo": "3T26"},
    {"company": "raizen", "metric": "mix_etanol", "valor": 53.0, "periodo": "3T26"},
]


def test_soma_metric_por_periodo():
    assert soma_metric(REGISTROS, "moagem", "3T26") == 108.5  # 24 + 80 + 4.5
    assert soma_metric(REGISTROS, "moagem", "3T25") == 105.4  # 23 + 78 + 4.4


def test_variacao_e_tendencia():
    atual = soma_metric(REGISTROS, "moagem", "3T26")
    ant = soma_metric(REGISTROS, "moagem", "3T25")
    pct = variacao_pct(atual, ant)
    assert pct == 2.9  # (108.5/105.4 - 1)*100
    assert tendencia(pct) == "em alta"


def test_tendencia_limites():
    assert tendencia(0.5) == "estável"
    assert tendencia(-3) == "em queda"
    assert tendencia(None) == "sem referência"


def test_mix_medio():
    m = mix_medio(REGISTROS, "3T26")
    assert m == {"acucar": 49.0, "etanol": 51.0}  # médias de 51/47 e 49/53


def test_variacao_zero_nao_quebra():
    assert variacao_pct(10, 0) is None
