"""Testa a filtragem de notícias (função pura)."""

from datetime import date

import pandas as pd

from src.services.news import TODAS, filter_articles

TODAY = date(2026, 6, 21)

ARTICLES = pd.DataFrame(
    [
        {"id": "a1", "titulo": "Moagem", "data_publicacao": "2026-06-21",
         "source_code": "novaCana", "regiao": "Centro-Sul", "segmento": "Açúcar"},
        {"id": "a2", "titulo": "CRA Raízen", "data_publicacao": "2026-06-21",
         "source_code": "valor", "regiao": "Centro-Sul", "segmento": "Etanol"},
        {"id": "a3", "titulo": "RenovaBio", "data_publicacao": "2026-06-19",
         "source_code": "epbr", "regiao": "Nacional", "segmento": "Etanol"},
        {"id": "a4", "titulo": "Antiga", "data_publicacao": "2026-06-01",
         "source_code": "reuters", "regiao": "Centro-Sul", "segmento": "Açúcar"},
    ]
)
MENTIONS = pd.DataFrame(
    [{"article_id": "a1", "company_code": "sao_martinho"},
     {"article_id": "a2", "company_code": "raizen"}]
)
WATCH = {"raizen", "sao_martinho"}


def test_periodo_corta_antigos():
    out = filter_articles(ARTICLES, MENTIONS, WATCH, periodo="7 dias", today=TODAY)
    assert "a4" not in set(out["id"])  # 01/06 está fora dos 7 dias
    assert len(out) == 3


def test_filtro_segmento():
    out = filter_articles(ARTICLES, MENTIONS, WATCH, periodo="30 dias",
                          segmento="Etanol", today=TODAY)
    assert set(out["id"]) == {"a2", "a3"}


def test_filtro_regiao_e_todas_nao_filtra():
    out = filter_articles(ARTICLES, MENTIONS, WATCH, periodo="30 dias",
                          regiao=TODAS, today=TODAY)
    assert len(out) == 4


def test_filtro_empresa():
    out = filter_articles(ARTICLES, MENTIONS, WATCH, periodo="30 dias",
                          empresa="raizen", today=TODAY)
    assert set(out["id"]) == {"a2"}


def test_only_watchlist():
    out = filter_articles(ARTICLES, MENTIONS, WATCH, periodo="30 dias",
                          only_watchlist=True, today=TODAY)
    assert set(out["id"]) == {"a1", "a2"}


def test_combina_filtros_sem_resultado():
    out = filter_articles(ARTICLES, MENTIONS, WATCH, periodo="30 dias",
                          empresa="raizen", segmento="Açúcar", today=TODAY)
    assert len(out) == 0
