"""Indicadores no estilo 'painel de mercado' — faixa de KPIs com variações.

Inspirado no layout do sugar-intel: cada indicador vira um card com o valor
atual, a data de referência e as variações em janelas (30d / 90d / 12m). Os
dados vêm do próprio banco (indicator_values), então isto é só a camada visual.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
from sqlalchemy import text

from src.persistence.db import get_engine

# cor por sinal de variação
_VERDE = "#1F7A4D"
_VERMELHO = "#B4462E"
_TINTA = "#18241F"
_TINTA_SUAVE = "#5C6B63"
_LINHA = "#E6E2D6"


def _serie(code: str) -> pd.DataFrame:
    """Histórico (data, valor) de um indicador, mais antigo -> mais novo."""
    with get_engine(readonly=True).connect() as conn:
        df = pd.read_sql_query(
            text("""SELECT data_referencia AS d, valor AS v
                    FROM indicator_values WHERE indicator_code = :c
                    ORDER BY data_referencia"""),
            conn, params={"c": code},
        )
    if not df.empty:
        df["d"] = pd.to_datetime(df["d"])
    return df


def _var(serie: pd.DataFrame, dias: int) -> float | None:
    """Variação % entre o último ponto e o ponto ~N dias antes."""
    if serie.empty:
        return None
    ultimo = serie.iloc[-1]
    alvo = ultimo["d"] - timedelta(days=dias)
    anteriores = serie[serie["d"] <= alvo]
    if anteriores.empty:
        return None
    base = anteriores.iloc[-1]["v"]
    if not base:
        return None
    return (ultimo["v"] - base) / base


def kpi_indicadores(codigos: list[tuple[str, str, str]]) -> str:
    """Monta a faixa de KPIs. codigos = [(code, rotulo, unidade), ...]."""
    cards = []
    for code, rotulo, unidade in codigos:
        serie = _serie(code)
        if serie.empty:
            cards.append(_card_vazio(rotulo, unidade))
            continue
        atual = serie.iloc[-1]
        cards.append(_card(rotulo, unidade, atual["v"], atual["d"].date(),
                           _var(serie, 30), _var(serie, 90), _var(serie, 365)))
    return ('<div style="display:flex;gap:12px;flex-wrap:wrap;margin:6px 0 20px">'
            + "".join(cards) + "</div>")


def _fmt_v(v: float, unidade: str) -> str:
    casas = 2 if abs(v) < 100 else 0
    s = f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def _chip(rotulo: str, var: float | None) -> str:
    if var is None:
        return (f'<span style="color:{_TINTA_SUAVE};font-size:11px">{rotulo} —</span>')
    cor = _VERDE if var >= 0 else _VERMELHO
    seta = "▲" if var >= 0 else "▼"
    return (f'<span style="color:{cor};font-size:11px;white-space:nowrap">'
            f'{rotulo} {seta} {abs(var) * 100:.1f}%</span>'.replace(".", ","))


def _card(rotulo, unidade, valor, ref, v30, v90, v365) -> str:
    chips = " · ".join([_chip("30d", v30), _chip("90d", v90), _chip("12m", v365)])
    return (
        f'<div style="flex:1;min-width:190px;background:#fff;border:1px solid {_LINHA};'
        f'border-radius:12px;padding:14px 16px">'
        f'<div style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;'
        f'color:{_TINTA_SUAVE}">{rotulo}</div>'
        f'<div style="font-size:23px;font-weight:800;color:{_TINTA};margin:4px 0 2px">'
        f'{_fmt_v(valor, unidade)} <span style="font-size:12px;font-weight:600;'
        f'color:{_TINTA_SUAVE}">{unidade}</span></div>'
        f'<div style="margin:6px 0 4px">{chips}</div>'
        f'<div style="font-size:11px;color:{_TINTA_SUAVE}">ref {ref.strftime("%d/%m/%Y")}</div>'
        f"</div>"
    )


def _card_vazio(rotulo, unidade) -> str:
    return (
        f'<div style="flex:1;min-width:190px;background:#FAF8F3;border:1px dashed {_LINHA};'
        f'border-radius:12px;padding:14px 16px">'
        f'<div style="font-size:11px;letter-spacing:.06em;text-transform:uppercase;'
        f'color:{_TINTA_SUAVE}">{rotulo}</div>'
        f'<div style="font-size:15px;font-weight:700;color:{_TINTA_SUAVE};margin:8px 0">'
        f'sem dado ainda</div>'
        f'<div style="font-size:11px;color:{_TINTA_SUAVE}">{unidade} · coleta planejada</div>'
        f"</div>"
    )


def serie_para_grafico(code: str, dias: int = 365) -> pd.DataFrame:
    """Série recente de um indicador, para o gráfico de linha."""
    serie = _serie(code)
    if serie.empty:
        return serie
    corte = serie.iloc[-1]["d"] - pd.Timedelta(days=dias)
    return serie[serie["d"] >= corte].rename(columns={"d": "Data", "v": "Valor"})
