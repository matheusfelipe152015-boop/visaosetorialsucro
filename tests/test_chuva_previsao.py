"""Testa o parser da previsão de chuva 14 dias (CSV do sugar-intel)."""


def test_parse_chuva_basico():
    from src.collectors.market.chuva_previsao import parse_chuva
    csv = (
        "data_coleta,cidade,ordem,data_prev,precip_mm,lat,lon,fonte_url\n"
        "2026-07-18,Ribeirão Preto,1,2026-07-18,0.0,-21.17,-47.81,https://open-meteo.com/\n"
        "2026-07-18,Ribeirão Preto,2,2026-07-19,5.2,-21.17,-47.81,https://open-meteo.com/\n"
    )
    linhas = parse_chuva(csv)
    assert len(linhas) == 2
    assert linhas[1]["precip_mm"] == 5.2
    assert linhas[0]["cidade"] == "Ribeirão Preto"


def test_parse_ignora_linha_invalida():
    from src.collectors.market.chuva_previsao import parse_chuva
    csv = (
        "data_coleta,cidade,ordem,data_prev,precip_mm,lat,lon,fonte_url\n"
        "2026-07-18,,1,2026-07-18,0.0,,,\n"          # sem cidade
        "2026-07-18,Bauru,2,data-ruim,3.0,,,\n"       # data inválida
        "2026-07-18,Bauru,3,2026-07-20,,,,\n"         # sem precip
        "2026-07-18,Bauru,4,2026-07-21,1.5,,,\n"      # ok
    )
    linhas = parse_chuva(csv)
    assert len(linhas) == 1
    assert linhas[0]["precip_mm"] == 1.5
