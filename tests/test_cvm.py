"""Testa o parser do coletor CVM, offline (CSV de exemplo no formato real)."""

from datetime import date

from src.collectors.market.cvm_financeiro import consolidar_divida, parse_csv_cvm

# CSV no formato da CVM (separador ';'). Inclui São Martinho (nossa) e uma
# empresa qualquer (deve ser ignorada). Colunas simplificadas às usadas.
SAMPLE = (
    "CNPJ_CIA;DT_FIM_EXERC;ORDEM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ESCALA_MOEDA\n"
    "51.466.860/0001-56;2026-03-31;ÚLTIMO;3.01;Receita;6.500.000;MIL\n"
    "51.466.860/0001-56;2026-03-31;ÚLTIMO;3.11;Lucro;850.000;MIL\n"
    "51.466.860/0001-56;2026-03-31;ÚLTIMO;2.01;Passivo Circulante;1.200.000;MIL\n"
    "51.466.860/0001-56;2026-03-31;ÚLTIMO;2.02;Passivo Não Circulante;3.800.000;MIL\n"
    "51.466.860/0001-56;2025-03-31;PENÚLTIMO;3.01;Receita;6.000.000;MIL\n"
    "99.999.999/0001-99;2026-03-31;ÚLTIMO;3.01;Receita;123;MIL\n"
)


def _idx(linhas):
    return {(r["company"], r["metric"]): r for r in linhas}


def test_extrai_receita_e_lucro():
    by = _idx(parse_csv_cvm(SAMPLE))
    assert by[("sao_martinho", "receita")]["valor"] == 6500000.0
    assert by[("sao_martinho", "lucro_liquido")]["valor"] == 850000.0
    assert by[("sao_martinho", "receita")]["unidade"] == "R$ mil"
    assert by[("sao_martinho", "receita")]["data_referencia"] == date(2026, 3, 31)


def test_ignora_outras_empresas():
    linhas = parse_csv_cvm(SAMPLE)
    empresas = {r["company"] for r in linhas}
    assert empresas == {"sao_martinho"}  # a 99.999... não entra


def test_ignora_exercicio_anterior():
    # a linha PENÚLTIMO (2025) não deve entrar
    datas = {r["data_referencia"] for r in parse_csv_cvm(SAMPLE)}
    assert date(2025, 3, 31) not in datas


def test_consolida_divida():
    linhas = consolidar_divida(parse_csv_cvm(SAMPLE))
    by = _idx(linhas)
    # 1.200.000 + 3.800.000 = 5.000.000
    assert by[("sao_martinho", "divida_total")]["valor"] == 5000000.0
    # os passivos individuais somem, viram divida_total
    assert ("sao_martinho", "passivo_circulante") not in by


def test_formato_decimal_americano_nao_infla():
    # formato real da CVM: ponto decimal. NÃO pode inflar (bug dos quatrilhões).
    from src.collectors.market.cvm_financeiro import _num
    assert _num("6431765.00") == 6431765.0
    assert _num("74317650.50") == 74317650.5
