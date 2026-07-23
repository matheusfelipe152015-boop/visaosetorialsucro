"""Catálogo canônico de fontes e indicadores da plataforma.

Este é DADO REAL do projeto (não demonstração): a lista do que a plataforma
cobre e de onde cada coisa vem. Fica aqui para ser usado tanto pela rotina de
coleta (jobs/run_daily.py) quanto pelo seed de demonstração.

register_catalog() cadastra fontes e indicadores de forma idempotente, sem
inserir nenhum valor — apenas o "mapa" do que existe.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

SOURCES = [
    # code, nome, instituicao, tier, tipo, licenca, automacao, freq, available, status
    ("bcb_sgs", "BCB · SGS", "Banco Central do Brasil", "A", "api", "aberta", 1, "daily", 1, "Atualizado"),
    ("anp", "ANP · dados abertos", "ANP", "A", "csv", "aberta", 1, "weekly", 1, "Atualizado"),
    ("conab", "CONAB", "CONAB", "A", "csv", "aberta", 1, "eventual", 1, "Atualizado"),
    ("comex", "Comex Stat · SECEX", "MDIC/SECEX", "A", "api", "aberta", 1, "monthly", 1, "Atualizado"),
    ("cvm", "CVM · dados abertos", "CVM", "A", "csv", "aberta", 1, "eventual", 1, "Atualizado"),
    ("ccee", "CCEE / ANEEL", "CCEE", "A", "portal", "a validar", 0, "weekly", 1, "Planejado"),
    ("usda", "USDA FAS · PSD", "USDA", "A", "api", "aberta", 1, "monthly", 1, "Planejado"),
    ("inmet", "INMET · estações automáticas", "INMET/MAPA", "A", "api", "aberta", 1, "weekly", 1, "Atualizado"),
    ("eia", "EIA", "U.S. Energy Information Adm.", "A", "api", "aberta", 1, "daily", 1, "Atualizado"),
    ("cepea", "CEPEA/ESALQ", "USP", "D", "scraping", "a validar", 0, "daily", 0, "Fonte indisponível"),
    ("ice", "ICE", "Intercontinental Exchange", "D", "api", "paga", 0, "daily", 1, "Atenção"),
    ("yahoo", "Yahoo Finance", "Yahoo (republica ICE/NYMEX)", "C", "api", "aberta", 1, "daily", 1, "Atualizado"),
    ("sugar_intel", "sugar-intel (open data)", "Igor Strongylis — dados abertos", "C", "csv", "aberta", 1, "daily", 1, "Atualizado"),
    ("b3", "B3", "B3 S.A.", "A", "api", "aberta", 1, "daily", 1, "Atualizado"),
    ("unica", "ÚNICA · UNICADATA", "ÚNICA", "B", "scraping", "a validar", 0, "biweekly", 1, "Desatualizado"),
    # Tier C — notícias (apenas metadados + resumo + link)
    ("novaCana", "novaCana", "novaCana", "C", "rss", "metadados+link", 1, "eventual", 1, "Atualizado"),
    ("valor", "Valor Econômico", "Globo", "C", "rss", "metadados+link", 1, "eventual", 1, "Atualizado"),
    ("reuters", "Reuters", "Reuters", "C", "rss", "metadados+link", 1, "eventual", 1, "Atualizado"),
    ("jornalcana", "JornalCana", "JornalCana", "C", "rss", "metadados+link", 1, "eventual", 1, "Atualizado"),
    ("epbr", "epbr", "epbr", "C", "rss", "metadados+link", 1, "eventual", 1, "Atualizado"),
    ("noticiasagricolas", "Notícias Agrícolas", "Notícias Agrícolas", "C", "rss", "metadados+link", 1, "eventual", 1, "Atualizado"),
]

INDICATORS = [
    # code, nome, categoria, unidade, moeda, escala, source, freq, destaque
    # Câmbio & macro
    ("usd_brl", "Câmbio USD/BRL (PTAX)", "Câmbio & macro", "BRL/USD", "BRL", "unit", "bcb_sgs", "daily", 1),
    ("selic_meta", "Selic meta", "Câmbio & macro", "% a.a.", None, "unit", "bcb_sgs", "daily", 0),
    ("ipca_mensal", "IPCA (mês)", "Câmbio & macro", "% mês", None, "unit", "bcb_sgs", "monthly", 0),
    ("igpm_mensal", "IGP-M (mês)", "Câmbio & macro", "% mês", None, "unit", "bcb_sgs", "monthly", 0),
    ("cdi_diario", "CDI", "Câmbio & macro", "% a.d.", None, "unit", "bcb_sgs", "daily", 0),
    # Petróleo & energia
    ("brent", "Brent", "Petróleo & energia", "US$/bbl", "USD", "unit", "yahoo", "daily", 1),
    ("pld_sudeste", "PLD — Sudeste/CO", "Petróleo & energia", "R$/MWh", "BRL", "unit", "ccee", "weekly", 0),
    # Açúcar
    ("sugar_ny11", "Açúcar NY nº 11", "Açúcar", "¢/lb", "USD", "unit", "yahoo", "daily", 1),
    ("acucar_cristal_sp", "Açúcar cristal (SP)", "Açúcar", "R$/sc 50kg", "BRL", "unit", "cepea", "daily", 0),
    ("acucar_londres5", "Açúcar branco — Londres nº 5", "Açúcar", "US$/t", "USD", "unit", "ice", "daily", 0),
    # Etanol
    ("etanol_hidratado", "Etanol hidratado (SP)", "Etanol", "R$/L", "BRL", "unit", "cepea", "daily", 1),
    ("etanol_anidro_sp", "Etanol anidro (SP)", "Etanol", "R$/L", "BRL", "unit", "cepea", "daily", 0),
    ("etanol_paulinia", "Etanol hidratado Paulínia", "Etanol", "R$/m³", "BRL", "unit", "sugar_intel", "daily", 1),
    ("wti", "WTI", "Petróleo & energia", "US$/bbl", "USD", "unit", "sugar_intel", "daily", 0),
    ("etanol_milho_total", "Etanol de milho — produção (Brasil)", "Etanol", "mil L", None, "unit", "sugar_intel", "eventual", 0),
    ("etanol_milho_anidro", "Etanol de milho anidro (Brasil)", "Etanol", "mil L", None, "unit", "sugar_intel", "eventual", 0),
    ("etanol_milho_hidratado", "Etanol de milho hidratado (Brasil)", "Etanol", "mil L", None, "unit", "sugar_intel", "eventual", 0),
    ("usda_acucar_consumo", "Consumo mundial de açúcar (USDA)", "Açúcar", "mil t", None, "unit", "sugar_intel", "eventual", 0),
    ("usda_stock_to_use", "Estoque/uso mundial de açúcar (USDA)", "Açúcar", "%", None, "unit", "sugar_intel", "eventual", 0),
    ("preco_gasolina", "Gasolina comum (revenda)", "Etanol", "R$/L", "BRL", "unit", "anp", "weekly", 0),
    ("preco_gasolina_aditivada", "Gasolina aditivada (revenda)", "Etanol", "R$/L", "BRL", "unit", "anp", "weekly", 0),
    ("preco_etanol", "Etanol hidratado (revenda)", "Etanol", "R$/L", "BRL", "unit", "anp", "weekly", 0),
    ("vendas_combustiveis", "Vendas de combustíveis/etanol", "Etanol", "m³", None, "unit", "anp", "monthly", 0),
    # Descarbonização
    ("cbio", "CBIO (preço)", "Descarbonização", "R$/un", "BRL", "unit", "b3", "daily", 1),
    # Produção & safra (ÚNICA)
    ("moagem_cs", "Moagem de cana (CS)", "Produção & safra", "Mt", None, "milhões", "unica", "biweekly", 0),
    ("producao_acucar", "Produção de açúcar", "Produção & safra", "Mt", None, "milhões", "unica", "biweekly", 0),
    ("producao_etanol", "Produção de etanol", "Produção & safra", "bi L", None, "bilhões", "unica", "biweekly", 0),
    ("mix_acucar_etanol", "Mix açúcar/etanol", "Produção & safra", "%", None, "unit", "unica", "biweekly", 0),
    ("atr_medio", "ATR médio", "Produção & safra", "kg/t", None, "unit", "unica", "biweekly", 0),
    # Comércio exterior
    ("exp_acucar", "Exportações de açúcar", "Comércio exterior", "US$ FOB", "USD", "unit", "comex", "monthly", 0),
    ("exp_etanol", "Exportações de etanol", "Comércio exterior", "US$ FOB", "USD", "unit", "comex", "monthly", 0),
    # Visão mundial (USDA)
    ("usda_acucar_prod", "Produção mundial de açúcar", "Visão mundial", "Mt", None, "milhões", "usda", "monthly", 0),
    ("usda_acucar_estoque", "Estoques mundiais de açúcar", "Visão mundial", "Mt", None, "milhões", "usda", "monthly", 0),
    # Safra & produção (CONAB)
    ("cana_producao", "Produção de cana (Brasil)", "Safra & produção", "mil t", None, "unit", "conab", "eventual", 1),
    ("cana_area_plantada", "Área plantada de cana", "Safra & produção", "mil ha", None, "unit", "conab", "eventual", 0),
    ("acucar_producao", "Produção de açúcar (Brasil)", "Safra & produção", "mil t", None, "unit", "conab", "eventual", 1),
    ("etanol_producao", "Produção de etanol (Brasil)", "Safra & produção", "mil L", None, "unit", "conab", "eventual", 1),
    ("cana_atr_medio", "ATR médio (Brasil)", "Safra & produção", "kg/t", None, "unit", "conab", "eventual", 0),
    ("paridade_etanol", "Paridade etanol/gasolina", "Etanol", "%", None, "unit", "anp", "weekly", 0),
]


def register_catalog(conn: Connection) -> None:
    """Cadastra fontes e indicadores (idempotente). Não insere valores."""
    for s in SOURCES:
        params = dict(zip("abcdefghij", s, strict=False))
        # campos booleanos: PostgreSQL exige true/false, não 1/0
        params["g"] = bool(params["g"])  # automacao_permitida
        params["i"] = bool(params["i"])  # available
        conn.execute(
            text(
                """INSERT INTO sources(code,nome,instituicao,tier,tipo_acesso,licenca,
                   automacao_permitida,frequencia_esperada,available,status)
                   VALUES(:a,:b,:c,:d,:e,:f,:g,:h,:i,:j)
                   ON CONFLICT(code) DO UPDATE SET available=excluded.available,
                   status=excluded.status"""
            ),
            params,
        )
    for ind in INDICATORS:
        params = dict(zip("abcdefghi", ind, strict=False))
        params["i"] = bool(params["i"])  # destaque
        conn.execute(
            text(
                """INSERT INTO indicators(code,nome,categoria,unidade,moeda,escala,source_code,frequencia,destaque)
                   VALUES(:a,:b,:c,:d,:e,:f,:g,:h,:i)
                   ON CONFLICT(code) DO UPDATE SET
                     nome=excluded.nome, categoria=excluded.categoria, unidade=excluded.unidade,
                     moeda=excluded.moeda, escala=excluded.escala, source_code=excluded.source_code,
                     frequencia=excluded.frequencia, destaque=excluded.destaque"""
            ),
            params,
        )
