"""Filtragem de notícias (função pura, sem dependência de UI).

Recebe os DataFrames já carregados e devolve os artigos que passam pelos
filtros selecionados. Mantido fora da página para ser testável isoladamente.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

PERIODO_DIAS = {"24h": 1, "48h": 2, "7 dias": 7, "30 dias": 30}
TODAS = "Todas"


def filter_articles(
    articles: pd.DataFrame,
    mentions: pd.DataFrame,
    watchlist: set[str],
    *,
    periodo: str = "7 dias",
    regiao: str | None = None,
    segmento: str | None = None,
    empresa: str | None = None,
    fonte: str | None = None,
    only_watchlist: bool = False,
    today: date | None = None,
) -> pd.DataFrame:
    """Aplica os filtros e devolve o subconjunto de artigos.

    `articles` deve conter: id, titulo, data_publicacao, source_code, regiao, segmento.
    `mentions` deve conter: article_id, company_code.
    `watchlist` é o conjunto de company_code marcados.
    Valores None ou "Todas" significam "sem filtro" naquele campo.
    """
    today = today or date.today()
    df = articles.copy()
    df["data_publicacao"] = pd.to_datetime(df["data_publicacao"]).dt.date

    cutoff = today - timedelta(days=PERIODO_DIAS.get(periodo, 7))
    df = df[df["data_publicacao"] >= cutoff]

    def _on(value: str | None) -> bool:
        return bool(value) and value != TODAS

    if _on(regiao):
        df = df[df["regiao"] == regiao]
    if _on(segmento):
        df = df[df["segmento"] == segmento]
    if _on(fonte):
        df = df[df["source_code"] == fonte]

    if _on(empresa) or only_watchlist:
        wanted = (
            set(mentions.loc[mentions["company_code"] == empresa, "article_id"])
            if _on(empresa)
            else None
        )
        watch_articles = (
            set(mentions.loc[mentions["company_code"].isin(watchlist), "article_id"])
            if only_watchlist
            else None
        )
        keep = set(df["id"])
        if wanted is not None:
            keep &= wanted
        if watch_articles is not None:
            keep &= watch_articles
        df = df[df["id"].isin(keep)]

    return df.sort_values("data_publicacao", ascending=False)
