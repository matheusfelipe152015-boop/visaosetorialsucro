"""Testa os parsers dos CSVs abertos do sugar-intel."""


def test_cepea_acucar():
    from src.collectors.market.sugar_intel_csv import CepeaAcucarSpCollector
    csv = "data,preco_r$_sc50kg,preco_us$\n2026-07-17,93.56,17.10\n"
    v = CepeaAcucarSpCollector().parse(csv)
    assert len(v) == 1
    assert v[0].indicator_code == "acucar_cristal_sp"
    assert v[0].valor == 93.56


def test_cepea_etanol_gera_dois():
    from src.collectors.market.sugar_intel_csv import CepeaEtanolSpCollector
    csv = ("semana_inicio,preco_hidratado_r$_l,preco_anidro_r$_l\n"
           "2026-07-13,2.13,2.45\n")
    v = CepeaEtanolSpCollector().parse(csv)
    codes = {x.indicator_code for x in v}
    assert codes == {"etanol_hidratado", "etanol_anidro_sp"}


def test_oil_brent():
    from src.collectors.market.sugar_intel_csv import OilBrentCollector
    csv = ("data,wti_usd_bbl,wti_tela,brent_usd_bbl,brent_tela,usd_brl_ptax\n"
           "2026-07-17,82.49,Q26,88.1,U26,5.1176\n")
    v = OilBrentCollector().parse(csv)
    assert len(v) == 1
    assert v[0].valor == 88.1


def test_unica_filtra_centro_sul_acumulado():
    from src.collectors.market.sugar_intel_csv import UnicaQuinzenalCollector
    csv = ("safra,quinzena_fim,regiao,tipo_secao,cana_mil_t,acucar_mil_t,"
           "etanol_anidro_mil_m3,etanol_hidratado_mil_m3,etanol_total_mil_m3,"
           "atr_mil_t,atr_kg_t_cana,litros_etanol_t_cana,kg_acucar_t_cana,"
           "mix_acucar_pct,mix_etanol_pct\n"
           "2024/2025,2026-04-01,Centro-Sul,acumulado,621927,40179,12366,22595,"
           "34961,87745,141.09,43.04,64.6,48.06,51.94\n"
           "2024/2025,2026-04-01,Norte-Nordeste,acumulado,10000,500,0,0,0,0,"
           "100,40,60,45,55\n")
    v = UnicaQuinzenalCollector().parse(csv)
    # só a linha Centro-Sul acumulado deve entrar (3 indicadores)
    assert len(v) == 3
    assert {x.indicator_code for x in v} == {"moagem_cs", "mix_acucar_etanol", "atr_medio"}


def test_ignora_valores_vazios():
    from src.collectors.market.sugar_intel_csv import CepeaAcucarSpCollector
    csv = "data,preco_r$_sc50kg,preco_us$\n2026-07-17,,17.10\ndata-ruim,90,10\n"
    v = CepeaAcucarSpCollector().parse(csv)
    assert len(v) == 0
