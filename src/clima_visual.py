"""Gráficos da aba Clima — previsão de chuva 14 dias e pluma ENSO (IRI).

A chuva vem da tabela chuva_previsao (Open-Meteo via sugar-intel) e a pluma da
tabela iri_plume (modelos IRI/CCSR). Ambas alimentadas pelo robô diário.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

from src.persistence.db import get_engine

VERDE = "#14573A"
AMBAR = "#C6881C"
TERRACOTA = "#B4462E"
AZUL = "#2F6F8F"
TINTA = "#18241F"
TINTA_SUAVE = "#5C6B63"
LINHA = "#E6E2D6"

_LAYOUT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
               font=dict(color=TINTA), margin=dict(l=10, r=10, t=30, b=10))


def _df(sql: str) -> pd.DataFrame:
    with get_engine(readonly=True).connect() as conn:
        return pd.read_sql_query(text(sql), conn)


# ── Chuva prevista 14 dias ────────────────────────────────────────────────

def fig_chuva_heatmap() -> go.Figure | None:
    """Mapa de calor cidade × dia com a chuva prevista (mm)."""
    d = _df("""SELECT cidade, data_prev, precip_mm FROM chuva_previsao
               WHERE data_coleta = (SELECT MAX(data_coleta) FROM chuva_previsao)
               ORDER BY data_prev""")
    if d.empty:
        return None
    d["data_prev"] = pd.to_datetime(d["data_prev"])
    piv = d.pivot_table(index="cidade", columns="data_prev", values="precip_mm",
                        aggfunc="sum").fillna(0)
    piv = piv.loc[piv.sum(axis=1).sort_values().index]
    rotulos = [c.strftime("%d/%m") for c in piv.columns]
    fig = go.Figure(go.Heatmap(
        z=piv.values, x=rotulos, y=list(piv.index),
        colorscale=[[0, "#F5F3EC"], [0.35, "#BBD3C6"], [1, AZUL]],
        showscale=True, colorbar=dict(title="mm", thickness=10),
        hovertemplate="<b>%{y}</b> · %{x}<br>%{z:.1f} mm<extra></extra>"))
    fig.update_layout(**_LAYOUT, height=max(340, 26 * len(piv) + 90),
                      xaxis_title="", yaxis_title="")
    return fig


def fig_chuva_acumulada() -> go.Figure | None:
    """Chuva acumulada nos 14 dias por cidade (mm)."""
    d = _df("""SELECT cidade, SUM(precip_mm) AS total FROM chuva_previsao
               WHERE data_coleta = (SELECT MAX(data_coleta) FROM chuva_previsao)
               GROUP BY cidade ORDER BY total""")
    if d.empty:
        return None
    fig = px.bar(d, x="total", y="cidade", orientation="h",
                 color_discrete_sequence=[AZUL], text=d["total"].round(0))
    fig.update_traces(textposition="outside", cliponaxis=False, textangle=0,
                      hovertemplate="<b>%{y}</b><br>%{x:.1f} mm em 14 dias<extra></extra>")
    fig.update_layout(**_LAYOUT, height=max(340, 26 * len(d) + 80),
                      xaxis=dict(title="mm acumulados",
                                 range=[0, max(float(d["total"].max()) * 1.2, 1)]),
                      yaxis_title="")
    return fig


# ── Pluma de previsão do ENSO ─────────────────────────────────────────────

def fig_iri_plume() -> go.Figure | None:
    """Projeções de anomalia Niño 3.4: média por tipo de modelo + faixa mín-máx."""
    d = _df("""SELECT data_prev, estacao, modelo, tipo, nino34_anom_c
               FROM iri_plume WHERE nino34_anom_c IS NOT NULL ORDER BY data_prev""")
    if d.empty:
        return None
    d["data_prev"] = pd.to_datetime(d["data_prev"])
    faixa = (d.groupby("data_prev")["nino34_anom_c"]
             .agg(["min", "max"]).reset_index().sort_values("data_prev"))
    rot = (d.drop_duplicates("data_prev").set_index("data_prev")["estacao"]
           .reindex(faixa["data_prev"]).fillna("").tolist())

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=faixa["data_prev"], y=faixa["max"], mode="lines",
                             line=dict(width=0), showlegend=False,
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=faixa["data_prev"], y=faixa["min"], mode="lines",
                             line=dict(width=0), fill="tonexty",
                             fillcolor="rgba(47,111,143,0.15)",
                             name="Faixa dos modelos", hoverinfo="skip"))
    cores = {"Dynamical": VERDE, "Statistical": AMBAR}
    for tipo, cor in cores.items():
        sub = d[d["tipo"] == tipo]
        if sub.empty:
            continue
        media = sub.groupby("data_prev")["nino34_anom_c"].mean().reset_index()
        nome = "Modelos dinâmicos" if tipo == "Dynamical" else "Modelos estatísticos"
        fig.add_trace(go.Scatter(x=media["data_prev"], y=media["nino34_anom_c"],
                                 mode="lines+markers", name=nome,
                                 line=dict(color=cor, width=2.5),
                                 hovertemplate="%{x|%b/%Y}<br>" + nome +
                                               ": %{y:.2f} °C<extra></extra>"))
    fig.add_hline(y=0.5, line_dash="dot", line_color=TERRACOTA,
                  annotation_text="El Niño", annotation_position="top left",
                  annotation_font_size=11)
    fig.add_hline(y=-0.5, line_dash="dot", line_color=AZUL,
                  annotation_text="La Niña", annotation_position="bottom left",
                  annotation_font_size=11)
    fig.add_hline(y=0, line_color=TINTA_SUAVE, line_width=1)
    fig.update_layout(**_LAYOUT, height=360,
                      xaxis=dict(title="", tickmode="array",
                                 tickvals=faixa["data_prev"], ticktext=rot),
                      yaxis_title="Anomalia Niño 3.4 (°C)",
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def resumo_chuva() -> dict | None:
    d = _df("""SELECT MIN(data_prev) AS ini, MAX(data_prev) AS fim,
                      COUNT(DISTINCT cidade) AS cidades, SUM(precip_mm) AS total
               FROM chuva_previsao
               WHERE data_coleta = (SELECT MAX(data_coleta) FROM chuva_previsao)""")
    if d.empty or pd.isna(d.iloc[0]["ini"]):
        return None
    linha = d.iloc[0]
    cidades = int(linha["cidades"]) or 1
    return {"ini": pd.to_datetime(linha["ini"]), "fim": pd.to_datetime(linha["fim"]),
            "cidades": cidades, "media_mm": float(linha["total"]) / cidades}
