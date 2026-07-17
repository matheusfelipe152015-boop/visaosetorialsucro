"""Testa a leitura e a média do coletor ANP, offline (CSV de exemplo)."""

from datetime import date

from src.collectors.market.anp_precos import parse_precos

# Mini CSV no mesmo formato da ANP: ';' separador, ',' decimal, latin-1.
# 2 postos de GASOLINA e 2 de ETANOL na mesma data -> média por produto.
SAMPLE = (
    "Regiao - Sigla;Estado - Sigla;Municipio;Produto;Valor de Venda;Data da Coleta\n"
    "SE;SP;SAO PAULO;GASOLINA;6,00;02/06/2026\n"
    "SE;SP;CAMPINAS;GASOLINA;6,20;02/06/2026\n"
    "S;PR;CURITIBA;ETANOL;4,00;02/06/2026\n"
    "S;PR;LONDRINA;ETANOL;4,40;02/06/2026\n"
).encode("latin-1")


def _by_code(values):
    return {v.indicator_code: v for v in values}


def test_media_por_combustivel():
    vals = parse_precos(SAMPLE)
    by = _by_code(vals)
    assert by["preco_gasolina"].valor == 6.10  # (6,00 + 6,20) / 2
    assert by["preco_etanol"].valor == 4.20    # (4,00 + 4,40) / 2


def test_metadados_rastreaveis():
    v = _by_code(parse_precos(SAMPLE))["preco_gasolina"]
    assert v.data_referencia == date(2026, 6, 2)
    assert v.unidade == "R$/L"
    assert v.source_code == "anp"
    assert v.moeda == "BRL"


def test_ignora_produto_desconhecido():
    csv = (
        "Produto;Valor de Venda;Data da Coleta\n"
        "DIESEL S10;6,50;02/06/2026\n"  # não mapeado -> ignorado
        "ETANOL;4,00;02/06/2026\n"
    ).encode("latin-1")
    vals = parse_precos(csv)
    codes = {v.indicator_code for v in vals}
    assert codes == {"preco_etanol"}


# ── por estado + paridade (novo) ──────────────────────────────────────────

SAMPLE_UF = (
    "Regiao - Sigla;Estado - Sigla;Municipio;Produto;Valor de Venda;Data da Coleta\n"
    "SE;SP;SAO PAULO;GASOLINA;6,00;10/06/2026\n"
    "SE;SP;CAMPINAS;GASOLINA;6,20;10/06/2026\n"
    "SE;SP;SAO PAULO;ETANOL;4,00;10/06/2026\n"
    "SE;SP;CAMPINAS;ETANOL;4,20;10/06/2026\n"
    "S;RS;PORTO ALEGRE;GASOLINA;6,00;10/06/2026\n"
    "S;RS;PORTO ALEGRE;ETANOL;5,10;10/06/2026\n"
).encode("latin-1")


def _uf_metric(linhas, uf, metric):
    return next(r for r in linhas if r["uf"] == uf and r["metric"] == metric)


def test_precos_por_estado():
    from src.collectors.market.anp_precos import parse_precos_uf
    linhas = parse_precos_uf(SAMPLE_UF)
    sp_gas = _uf_metric(linhas, "SP", "preco_gasolina")
    assert sp_gas["valor"] == 6.10          # média de 6,00 e 6,20
    assert sp_gas["regiao"] == "Sudeste"    # região preenchida (para o mapa)
    assert _uf_metric(linhas, "SP", "preco_etanol")["valor"] == 4.10


def test_paridade_etanol_gasolina_por_estado():
    from src.collectors.market.anp_precos import parse_precos_uf
    linhas = parse_precos_uf(SAMPLE_UF)
    # SP: etanol 4,10 / gasolina 6,10 = 67,2% -> abaixo de 70%, etanol COMPENSA
    sp = _uf_metric(linhas, "SP", "paridade_etanol")
    assert abs(sp["valor"] - 67.2) < 0.2
    assert sp["unidade"] == "%"
    # RS: etanol 5,10 / gasolina 6,00 = 85% -> acima de 70%, NÃO compensa
    rs = _uf_metric(linhas, "RS", "paridade_etanol")
    assert abs(rs["valor"] - 85.0) < 0.2


def test_periodo_e_mes_da_pesquisa():
    from src.collectors.market.anp_precos import parse_precos_uf
    linhas = parse_precos_uf(SAMPLE_UF)
    assert all(r["periodo"] == "2026-06" for r in linhas)
