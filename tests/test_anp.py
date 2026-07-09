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
