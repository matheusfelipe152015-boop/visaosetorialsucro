"""Popula o banco com dados de DEMONSTRAÇÃO (claramente sinalizados na UI).

Objetivo: permitir abrir o app e ver o design sem depender de rede ou Supabase.
Os números aqui são ilustrativos. A coleta real (jobs/run_daily.py) substitui o
câmbio por dados verdadeiros do BCB. NÃO usar estes valores para análise.
"""

from __future__ import annotations

import math
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text

from src.catalog import INDICATORS, register_catalog
from src.persistence.db import get_engine, init_schema

TOPICS = [
    ("producao_safra", "Produção & safra"),
    ("captacoes", "Captações"),
    ("comex", "Comércio exterior"),
    ("biometano", "Biometano"),
    ("renovabio", "RenovaBio"),
    ("regulacao", "Regulação"),
]

# titulo, fonte, dias_atras, empresa|None, [temas], regiao, segmento
NEWS = [
    ("Grupo eleva guidance de moagem após chuvas no Centro-Sul", "novaCana", 0,
     "sao_martinho", ["producao_safra"], "Centro-Sul", "Açúcar"),
    ("Emissão de CRA de R$ 1,2 bi é precificada com forte demanda", "valor", 0,
     "raizen", ["captacoes"], "Centro-Sul", "Etanol"),
    ("Exportações de açúcar recuam na 2ª quinzena, aponta preliminar", "reuters", 1,
     None, ["comex"], "Centro-Sul", "Açúcar"),
    ("Planta de biometano entra em fase de comissionamento", "jornalcana", 1,
     "adecoagro", ["biometano"], "Centro-Sul", "Biometano"),
    ("RenovaBio: metas de 2027 entram em consulta pública", "epbr", 2,
     None, ["renovabio", "regulacao"], "Nacional", "Etanol"),
]

WATCHLIST = ["raizen", "sao_martinho"]

COMPANIES = [
    ("raizen", "Raízen", "RAIZ4", "publica", "1", 1),
    ("sao_martinho", "São Martinho", "SMTO3", "publica", "1", 1),
    ("jalles", "Jalles Machado", "JALL3", "publica", "1", 2),
    ("adecoagro", "Adecoagro", "AGRO", "publica", "1", 2),
    ("cosan", "Cosan", "CSAN3", "publica", "1", 2),
    ("ctc", "CTC · Centro de Tecnologia Canavieira", "CTCA3", "publica", "2", 3),
]


def _usd_series(n: int = 140) -> list[tuple[date, float]]:
    base = 5.05
    out = []
    for i in range(n):
        d = date.today() - timedelta(days=n - i)
        if d.weekday() >= 5:  # pula fim de semana
            continue
        val = base + 0.35 * math.sin(i / 16) + 0.0022 * i
        out.append((d, round(val, 4)))
    return out


def run() -> None:
    init_schema()
    eng = get_engine()
    now = datetime.utcnow()
    with eng.begin() as c:
        # catálogo de fontes e indicadores vem do módulo central (dado real)
        register_catalog(c)

        # série do dólar (demo) + último valor dos demais
        for d, v in _usd_series():
            c.execute(
                text(
                    """INSERT INTO indicator_values(id,indicator_code,source_code,data_referencia,
                       data_publicacao,data_coleta,valor,unidade,moeda,escala,collector_version,status_validacao)
                       VALUES(:id,'usd_brl','bcb_sgs',:d,:d,:t,:v,'BRL/USD','BRL','unit','demo','ok')
                       ON CONFLICT(indicator_code,data_referencia,source_code) DO NOTHING"""
                ),
                {"id": uuid.uuid4().hex, "d": d, "t": now, "v": v},
            )
        latest = {"sugar_ny11": 18.74, "etanol_hidratado": 2.612, "brent": 71.20, "cbio": 64.50}
        for code, val in latest.items():
            src = next(i[6] for i in INDICATORS if i[0] == code)
            c.execute(
                text(
                    """INSERT INTO indicator_values(id,indicator_code,source_code,data_referencia,
                       data_publicacao,data_coleta,valor,unidade,collector_version,status_validacao)
                       VALUES(:id,:code,:src,:d,:d,:t,:v,'demo','demo','ok')
                       ON CONFLICT(indicator_code,data_referencia,source_code) DO NOTHING"""
                ),
                {"id": uuid.uuid4().hex, "code": code, "src": src,
                 "d": date.today() - timedelta(days=1), "t": now, "v": val},
            )

        # preços de combustível da ANP (demo). Pesquisa é semanal (ref = sexta passada).
        ref_anp = date.today() - timedelta(days=(date.today().weekday() + 3) % 7 + 1)
        anp_demo = {"preco_gasolina": 6.19, "preco_gasolina_aditivada": 6.34, "preco_etanol": 4.27}
        for code, val in anp_demo.items():
            c.execute(
                text(
                    """INSERT INTO indicator_values(id,indicator_code,source_code,data_referencia,
                       data_publicacao,data_coleta,valor,unidade,moeda,escala,collector_version,status_validacao)
                       VALUES(:id,:code,'anp',:d,:d,:t,:v,'R$/L','BRL','unit','demo','ok')
                       ON CONFLICT(indicator_code,data_referencia,source_code) DO NOTHING"""
                ),
                {"id": uuid.uuid4().hex, "code": code, "d": ref_anp, "t": now, "v": val},
            )

        # exportações de açúcar/etanol da Comex Stat (demo). Mensal; ref = dia 1.
        # 6 meses por produto, em US$ FOB (valores ilustrativos).
        hoje = date.today()
        comex_demo = {
            "exp_acucar": [980_000_000, 1_050_000_000, 1_120_000_000, 1_010_000_000, 1_180_000_000, 1_240_000_000],
            "exp_etanol": [210_000_000, 235_000_000, 198_000_000, 252_000_000, 246_000_000, 268_000_000],
        }
        for code, serie in comex_demo.items():
            for i, val in enumerate(serie):
                # meses retroativos: i=0 é o mês mais antigo; último é o mês anterior
                offset = len(serie) - i  # 6..1 meses atrás
                m_total = hoje.year * 12 + (hoje.month - 1) - offset
                ref = date(m_total // 12, m_total % 12 + 1, 1)
                c.execute(
                    text(
                        """INSERT INTO indicator_values(id,indicator_code,source_code,data_referencia,
                           data_publicacao,data_coleta,valor,unidade,moeda,escala,collector_version,status_validacao)
                           VALUES(:id,:code,'comex',:d,:d,:t,:v,'US$ FOB','USD','unit','demo','ok')
                           ON CONFLICT(indicator_code,data_referencia,source_code) DO NOTHING"""
                    ),
                    {"id": uuid.uuid4().hex, "code": code, "d": ref, "t": now, "v": float(val)},
                )

        # chuva por estado (demo). 3 períodos; mm observado + normal histórica.
        # Valores ilustrativos com padrão sazonal plausível (chove mais no N/Centro-Sul no verão).
        import random as _rnd

        _rnd.seed(42)
        from src.services.chuva import REGIAO_POR_UF
        base_normal = {  # normal mensal aproximada por região (mm) — ilustrativo
            "Norte": 180, "Nordeste": 90, "Centro-Oeste": 150, "Sudeste": 140, "Sul": 130,
        }
        periodos = {"semanal": (7, 0.25), "mensal": (30, 1.0), "trimestral": (90, 3.0)}
        for uf, regiao in REGIAO_POR_UF.items():
            normal_mes = base_normal[regiao]
            for periodo, (dias, fator) in periodos.items():
                normal = normal_mes * fator
                # observado varia ±40% em torno da normal
                mm = round(normal * _rnd.uniform(0.6, 1.4), 1)
                ref_chuva = date.today() - timedelta(days=dias)
                c.execute(
                    text(
                        """INSERT INTO rainfall(id,source_code,uf,regiao,periodo,data_referencia,
                           mm,normal_mm,data_coleta,collector_version,status_validacao)
                           VALUES(:id,'inmet',:uf,:reg,:per,:d,:mm,:nm,:t,'demo','ok')
                           ON CONFLICT(uf,periodo,data_referencia,source_code) DO NOTHING"""
                    ),
                    {"id": uuid.uuid4().hex, "uf": uf, "reg": regiao, "per": periodo,
                     "d": ref_chuva, "mm": mm, "nm": round(normal, 1), "t": now},
                )

        # ── dados operacionais das usinas (demo) ──────────────────────────
        # cadastra as empresas primeiro (as métricas dependem delas)
        for code, nome, tk, cls, tier, prio in COMPANIES:
            c.execute(
                text(
                    """INSERT INTO companies(code,nome,ticker,classificacao,tier,prioridade)
                       VALUES(:a,:b,:c,:d,:e,:f) ON CONFLICT(code) DO NOTHING"""
                ),
                {"a": code, "b": nome, "c": tk, "d": cls, "e": tier, "f": prio},
            )

        # moagem (Mt), mix açúcar/etanol (%), produção açúcar (kt) e etanol (mil m³).
        # Dois períodos para permitir leitura de tendência. Valores ilustrativos.
        op_demo = {
            # company: { periodo: {metric: valor} }
            "sao_martinho": {
                "3T26": {"moagem": 24.1, "mix_acucar": 51, "mix_etanol": 49, "prod_acucar": 1320, "prod_etanol": 980, "atr": 138.5},
                "3T25": {"moagem": 23.2, "mix_acucar": 49, "mix_etanol": 51, "prod_acucar": 1250, "prod_etanol": 1010, "atr": 137.0},
            },
            "raizen": {
                "3T26": {"moagem": 79.8, "mix_acucar": 47, "mix_etanol": 53, "prod_acucar": 4100, "prod_etanol": 3600, "atr": 134.2},
                "3T25": {"moagem": 82.5, "mix_acucar": 48, "mix_etanol": 52, "prod_acucar": 4300, "prod_etanol": 3500, "atr": 135.1},
            },
            "jalles": {
                "3T26": {"moagem": 4.6, "mix_acucar": 44, "mix_etanol": 56, "prod_acucar": 210, "prod_etanol": 260, "atr": 141.0},
                "3T25": {"moagem": 4.4, "mix_acucar": 42, "mix_etanol": 58, "prod_acucar": 195, "prod_etanol": 270, "atr": 140.2},
            },
        }
        unidades = {"moagem": "Mt", "mix_acucar": "%", "mix_etanol": "%",
                    "prod_acucar": "kt", "prod_etanol": "mil m³", "atr": "kg/t"}
        for empresa, periodos_emp in op_demo.items():
            for periodo, metrics in periodos_emp.items():
                ref_op = date.today() - timedelta(days=30 if periodo.endswith("26") else 395)
                for metric, val in metrics.items():
                    c.execute(
                        text(
                            """INSERT INTO company_metrics(id,company_code,metric,grupo,safra,periodo,
                               data_referencia,valor,unidade,fonte,data_publicacao,data_coleta,
                               collector_version,status_validacao)
                               VALUES(:id,:co,:m,'operacional',:sf,:per,:d,:v,:u,'release_producao',:d,:t,'demo','ok')
                               ON CONFLICT(company_code,metric,periodo,fonte) DO NOTHING"""
                        ),
                        {"id": uuid.uuid4().hex, "co": empresa, "m": metric,
                         "sf": "2025/26" if periodo.endswith("26") else "2024/25",
                         "per": periodo, "d": ref_op, "v": float(val), "u": unidades[metric], "t": now},
                    )

        for code, nome in TOPICS:
            c.execute(
                text("INSERT INTO news_topics(code,nome) VALUES(:a,:b) ON CONFLICT(code) DO NOTHING"),
                {"a": code, "b": nome},
            )

        for cc in WATCHLIST:
            c.execute(
                text("INSERT INTO watchlists(company_code) VALUES(:c) ON CONFLICT(company_code) DO NOTHING"),
                {"c": cc},
            )

        for i, (titulo, src, days_ago, empresa, temas, regiao, segmento) in enumerate(NEWS):
            url = f"demo:{i}"
            c.execute(
                text(
                    """INSERT INTO news_articles(id,source_code,titulo,resumo,url_canonica,
                       data_publicacao,data_coleta,idioma,pais,status_coleta,regiao,segmento)
                       VALUES(:id,:src,:t,:r,:u,:d,:dc,'pt','BR','ok',:reg,:seg)
                       ON CONFLICT(url_canonica) DO NOTHING"""
                ),
                {"id": uuid.uuid4().hex, "src": src, "t": titulo, "r": "Resumo de demonstração.",
                 "u": url, "d": date.today() - timedelta(days=days_ago),
                 "dc": now, "reg": regiao, "seg": segmento},
            )
            # resolve o id real (recém-inserido ou já existente) para manter a FK
            art_id = c.execute(
                text("SELECT id FROM news_articles WHERE url_canonica=:u"), {"u": url}
            ).scalar_one()
            if empresa:
                c.execute(
                    text(
                        """INSERT INTO article_company_mentions(article_id,company_code)
                           VALUES(:a,:c) ON CONFLICT(article_id,company_code) DO NOTHING"""
                    ),
                    {"a": art_id, "c": empresa},
                )
            for tp in temas:
                c.execute(
                    text(
                        """INSERT INTO article_topics(article_id,topic_code)
                           VALUES(:a,:t) ON CONFLICT(article_id,topic_code) DO NOTHING"""
                    ),
                    {"a": art_id, "t": tp},
                )
    print("Seed de demonstração aplicado.")


if __name__ == "__main__":
    run()
