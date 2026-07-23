"""Gráficos da UNICA para a aba Safra — moagem, mix e ATR do Centro-Sul.

Lê o CSV quinzenal da UNICA (via coletor sugar-intel) direto da fonte, para
ter a granularidade quinzenal da safra corrente. As visões: evolução da moagem
acumulada, do mix açúcar/etanol e do ATR médio.
"""

from __future__ import annotations

import csv
import io

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

VERDE = "#14573A"
AMBAR = "#C6881C"
TINTA = "#18241F"
LINHA = "#E6E2D6"
CSV_URL = "https://strongylis.github.io/sugar-intel/data/unica_quinzenal.csv"
_HEADERS = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/126.0.0.0 Safari/537.36")}

_LAYOUT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
               font=dict(color=TINTA), margin=dict(l=10, r=10, t=30, b=10))


def _num(v):
    s = str(v or "").strip().replace(",", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def carregar_unica(texto: str | None = None) -> pd.DataFrame:
    """Lê o CSV quinzenal da UNICA (baixa se texto não for passado)."""
    if texto is None:
        resp = httpx.get(CSV_URL, timeout=60, follow_redirects=True, headers=_HEADERS)
        resp.raise_for_status()
        texto = resp.content.decode("utf-8", errors="replace")
    linhas = []
    for r in csv.DictReader(io.StringIO(texto)):
        linhas.append({
            "safra": (r.get("safra") or "").strip(),
            "quinzena_fim": (r.get("quinzena_fim") or "").strip(),
            "regiao": (r.get("regiao") or "").strip(),
            "tipo_secao": (r.get("tipo_secao") or "").strip(),
            "cana_mil_t": _num(r.get("cana_mil_t")),
            "acucar_mil_t": _num(r.get("acucar_mil_t")),
            "etanol_total_mil_m3": _num(r.get("etanol_total_mil_m3")),
            "atr_kg_t_cana": _num(r.get("atr_kg_t_cana")),
            "mix_acucar_pct": _num(r.get("mix_acucar_pct")),
            "mix_etanol_pct": _num(r.get("mix_etanol_pct")),
        })
    df = pd.DataFrame(linhas)
    if not df.empty:
        df["quinzena_fim"] = pd.to_datetime(df["quinzena_fim"], errors="coerce")
    return df


def _centro_sul_acumulado(df: pd.DataFrame) -> pd.DataFrame:
    d = df[(df["regiao"] == "Centro-Sul") & (df["tipo_secao"] == "acumulado")].copy()
    return d.sort_values("quinzena_fim")


def fig_moagem(df: pd.DataFrame) -> go.Figure | None:
    d = _centro_sul_acumulado(df).dropna(subset=["cana_mil_t"])
    if d.empty:
        return None
    d["safra_lbl"] = d["safra"]
    fig = px.bar(d, x="safra_lbl", y="cana_mil_t", color_discrete_sequence=[VERDE],
                 text=(d["cana_mil_t"] / 1000).round(1))
    fig.update_traces(texttemplate="%{text} mi t", textposition="outside")
    fig.update_layout(**_LAYOUT, height=320, xaxis_title="Safra",
                      yaxis_title="Cana moída (mil t)")
    return fig


def fig_mix(df: pd.DataFrame) -> go.Figure | None:
    d = _centro_sul_acumulado(df).dropna(subset=["mix_acucar_pct"])
    if d.empty:
        return None
    fig = go.Figure()
    fig.add_bar(x=d["safra"], y=d["mix_acucar_pct"], name="Açúcar",
                marker_color=VERDE, text=d["mix_acucar_pct"].round(1),
                textposition="inside")
    fig.add_bar(x=d["safra"], y=d["mix_etanol_pct"], name="Etanol",
                marker_color=AMBAR, text=d["mix_etanol_pct"].round(1),
                textposition="inside")
    fig.update_layout(**_LAYOUT, height=320, barmode="stack",
                      yaxis_title="Mix (%)", xaxis_title="Safra",
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def fig_atr(df: pd.DataFrame) -> go.Figure | None:
    d = _centro_sul_acumulado(df).dropna(subset=["atr_kg_t_cana"])
    if d.empty:
        return None
    fig = px.line(d, x="safra", y="atr_kg_t_cana", markers=True,
                  color_discrete_sequence=[VERDE])
    fig.update_traces(text=d["atr_kg_t_cana"].round(1), textposition="top center",
                      mode="lines+markers+text")
    fig.update_layout(**_LAYOUT, height=320, yaxis_title="ATR (kg/t cana)",
                      xaxis_title="Safra")
    return fig


def resumo_safra_atual(df: pd.DataFrame) -> dict | None:
    d = _centro_sul_acumulado(df)
    if d.empty:
        return None
    ult = d.iloc[-1]
    return {
        "safra": ult["safra"],
        "cana_mil_t": ult["cana_mil_t"],
        "acucar_mil_t": ult["acucar_mil_t"],
        "etanol_mil_m3": ult["etanol_total_mil_m3"],
        "atr": ult["atr_kg_t_cana"],
        "mix_acucar": ult["mix_acucar_pct"],
    }
