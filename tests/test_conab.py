"""Testa o parser do coletor CONAB (offline, formato real do arquivo)."""

from datetime import date

from src.collectors.market.conab_cana import (
    _data_da_safra,
    _num,
    agrega_brasil,
    parse_conab_uf,
)

CABECALHO = (
    "ano_agricola;dsc_safra_previsao;uf;produto;id_produto;area_plantada_mil_ha;"
    "producao_mil_t;dsc_situacao_levantamento;producao_acucar_mil_t;"
    "producao_etanol_anidro_mil_l;producao_etanol_hidratado_mil_l;"
    "producao_etanol_total_mil_l;produtcao_atr_kg_t\n"
)
# Trecho REAL do arquivo (SP e GO, safra 2025/26)
SAMPLE = CABECALHO + (
    "2025/26;UNICA;SP;CANA DE ACUCAR;4238;4436,5;347937.2;PREVISAO;26266.9;"
    "5253655;7185712.1;12439367;137.4\n"
    "2025/26;UNICA;GO;CANA DE ACUCAR;4238;1030,7;80140.8;PREVISAO;3090.9;"
    "1205784.2;3345611.6;4551395.8;134.5\n"
)


def test_num_aceita_virgula_e_ponto():
    assert _num("4436,5") == 4436.5       # área: vírgula decimal
    assert _num("347937.2") == 347937.2   # produção: ponto decimal
    assert _num("") is None


def test_data_da_safra():
    assert _data_da_safra("2025/26") == date(2026, 3, 31)
    assert _data_da_safra("2005/06") == date(2006, 3, 31)
    assert _data_da_safra("lixo") is None


def test_parse_por_uf():
    linhas = parse_conab_uf(SAMPLE)
    ufs = {r["uf"] for r in linhas}
    assert ufs == {"SP", "GO"}
    sp_prod = next(r for r in linhas if r["uf"] == "SP" and r["metric"] == "cana_producao")
    assert sp_prod["valor"] == 347937.2
    assert sp_prod["regiao"] == "Sudeste"   # região preenchida (para o mapa)
    go_prod = next(r for r in linhas if r["uf"] == "GO" and r["metric"] == "cana_producao")
    assert go_prod["regiao"] == "Centro-Oeste"


def test_agrega_brasil_soma_producao():
    vals = {v.indicator_code: v for v in agrega_brasil(parse_conab_uf(SAMPLE))}
    assert vals["cana_producao"].valor == 428078.0    # 347937.2 + 80140.8
    assert vals["cana_area_plantada"].valor == 5467.2  # 4436,5 + 1030,7
    assert vals["acucar_producao"].valor == 29357.8


def test_atr_brasil_e_media_ponderada():
    vals = {v.indicator_code: v for v in agrega_brasil(parse_conab_uf(SAMPLE))}
    atr = vals["cana_atr_medio"].valor
    esperado = (137.4 * 347937.2 + 134.5 * 80140.8) / (347937.2 + 80140.8)
    assert abs(atr - round(esperado, 1)) < 0.05
    assert 134.5 <= atr <= 137.4   # entre os dois; NÃO é a soma (271.9)


def test_metadados_rastreaveis():
    v = agrega_brasil(parse_conab_uf(SAMPLE))[0]
    assert v.source_code == "conab"
    assert v.data_referencia == date(2026, 3, 31)
    assert "conab.gov.br" in v.url_original
