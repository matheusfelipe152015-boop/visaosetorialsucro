"""Testa o parser do coletor CVM, offline."""

from datetime import date

from src.collectors.market.cvm_financeiro import consolidar_divida, parse_csv_cvm

SAMPLE = (
    "CNPJ_CIA;DT_FIM_EXERC;ORDEM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ESCALA_MOEDA\n"
    "51.466.860/0001-56;2026-03-31;\u00daLTIMO;3.01;Receita;6.500.000;MIL\n"
    "51.466.860/0001-56;2026-03-31;\u00daLTIMO;3.11;Lucro;850.000;MIL\n"
    "51.466.860/0001-56;2026-03-31;\u00daLTIMO;2.01;Passivo Circ;1.200.000;MIL\n"
    "51.466.860/0001-56;2026-03-31;\u00daLTIMO;2.02;Passivo Nao Circ;3.800.000;MIL\n"
    "51.466.860/0001-56;2025-03-31;PEN\u00daLTIMO;3.01;Receita;6.000.000;MIL\n"
    "99.999.999/0001-99;2026-03-31;\u00daLTIMO;3.01;Receita;123;MIL\n"
)


def _idx(linhas):
    return {(r["company"], r["metric"]): r for r in linhas}


def test_extrai_receita_e_lucro():
    by = _idx(parse_csv_cvm(SAMPLE))
    assert by[("sao_martinho", "receita")]["valor"] == 6500000.0
    assert by[("sao_martinho", "lucro_liquido")]["valor"] == 850000.0
    assert by[("sao_martinho", "receita")]["data_referencia"] == date(2026, 3, 31)


def test_ignora_outras_empresas():
    empresas = {r["company"] for r in parse_csv_cvm(SAMPLE)}
    assert empresas == {"sao_martinho"}


def test_ignora_exercicio_anterior():
    datas = {r["data_referencia"] for r in parse_csv_cvm(SAMPLE)}
    assert date(2025, 3, 31) not in datas


def test_consolida_divida():
    by = _idx(consolidar_divida(parse_csv_cvm(SAMPLE)))
    assert by[("sao_martinho", "divida_total")]["valor"] == 5000000.0
    assert ("sao_martinho", "passivo_circulante") not in by
