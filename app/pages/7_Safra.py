"""Pagina 7 — Safra: mapa da producao de cana por estado (CONAB)."""

from __future__ import annotations

import os as _os
import sys as _sys

_r = _os.path.abspath(_os.path.dirname(__file__))
while _r != "/" and not _os.path.isdir(_os.path.join(_r, "src")):
    _r = _os.path.dirname(_r)
if _r not in _sys.path:
    _sys.path.insert(0, _r)

import json
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from src.app_auth import exigir_login
from src.persistence.db import fetch_df, init_schema
from src.theme import apply_theme

st.set_page_config(page_title="CANAVIS · Safra", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

GEOJSON = Path(_r) / "assets" / "geo" / "br_estados.geojson"


@st.cache_data
def carrega_geo():
    return json.loads(GEOJSON.read_text(encoding="utf-8"))


METRICAS = {
    "cana_producao": ("Producao de cana", "mil t", [[0, "#F0E0BC"], [0.5, "#6FB28C"], [1, "#0E3F2A"]]),
    "acucar_producao": ("Producao de acucar", "mil t", [[0, "#FBF3E0"], [0.5, "#E0B457"], [1, "#8A5D0F"]]),
    "etanol_producao": ("Producao de etanol", "mil L", [[0, "#E8F0EC"], [0.5, "#5FA37C"], [1, "#14573A"]]),
    "cana_area_plantada": ("Area plantada", "mil ha", [[0, "#EFEBE0"], [0.5, "#9BB09F"], [1, "#2E4A38"]]),
    "cana_atr_medio": ("ATR medio", "kg/t", [[0, "#F4F1E9"], [0.5, "#C6881C"], [1, "#7A4E08"]]),
}

st.markdown('<div class="eyebrow">07 · Safra — producao por estado</div>', unsafe_allow_html=True)
st.title("Mapa da safra")

dados_todos = fetch_df(
    "SELECT uf, regiao, safra, metric, valor, unidade FROM safra_uf WHERE source_code = 'conab'"
)

if dados_todos.empty:
    st.info("Sem dados de safra ainda. Rode `python3.12 jobs/run_daily.py` para coletar da CONAB.")
    st.stop()

c1, c2 = st.columns([1, 1])
safras = sorted(dados_todos["safra"].unique(), reverse=True)
safra = c1.selectbox("Safra", safras, index=0)
metrica_nome = c2.selectbox("Indicador", [v[0] for v in METRICAS.values()], index=0)
metrica = next(k for k, v in METRICAS.items() if v[0] == metrica_nome)
label, unidade, escala = METRICAS[metrica]

dados = dados_todos[
    (dados_todos["safra"] == safra) & (dados_todos["metric"] == metrica)
].copy()

if dados.empty:
    st.warning("Sem dados para essa combinacao.")
    st.stop()

geo = carrega_geo()

total = dados["valor"].sum()
lider = dados.loc[dados["valor"].idxmax()]
k1, k2, k3 = st.columns(3)
agregado = "media" if metrica == "cana_atr_medio" else "total"
valor_agregado = dados["valor"].mean() if metrica == "cana_atr_medio" else total
k1.markdown(
    f'<div class="cv-kpi"><div class="nm">{label} · Brasil ({agregado})</div>'
    f'<div class="val">{valor_agregado:,.0f}<span style="font-size:13px"> {unidade}</span></div>'
    f'<div style="margin-top:6px"><span class="src">safra {safra}</span></div></div>',
    unsafe_allow_html=True,
)
k2.markdown(
    f'<div class="cv-kpi"><div class="nm">Maior produtor</div>'
    f'<div class="val">{lider["uf"]}</div>'
    f'<div style="margin-top:6px"><span class="src">{lider["valor"]:,.0f} {unidade}</span></div></div>',
    unsafe_allow_html=True,
)
k3.markdown(
    f'<div class="cv-kpi"><div class="nm">Estados com producao</div>'
    f'<div class="val">{len(dados)}</div>'
    f'<div style="margin-top:6px"><span class="src">na safra {safra}</span></div></div>',
    unsafe_allow_html=True,
)

fig = go.Figure(
    go.Choropleth(
        geojson=geo,
        locations=dados["uf"],
        featureidkey="properties.sigla",
        z=dados["valor"],
        colorscale=escala,
        marker_line_color="white",
        marker_line_width=0.6,
        colorbar=dict(title=f"{label}<br>({unidade})", thickness=12, len=0.7),
        customdata=dados[["regiao"]],
        hovertemplate=(
            "<b>%{location}</b> (%{customdata[0]})<br>"
            + label + ": %{z:,.1f} " + unidade + "<extra></extra>"
        ),
    )
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin=dict(l=0, r=0, t=10, b=0), height=520,
    paper_bgcolor="rgba(0,0,0,0)", geo_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.markdown("##### Ranking por estado")
rank = dados.sort_values("valor", ascending=False)[["uf", "regiao", "valor"]].head(10)
rank.columns = ["UF", "Regiao", f"{label} ({unidade})"]
st.dataframe(rank.set_index("UF"), width="stretch")

st.markdown(
    '<div class="src" style="margin-top:14px;line-height:1.6">Fonte: CONAB — Portal de '
    "Informacoes Agropecuarias, Serie Historica da Cana-de-acucar. Levantamentos "
    "quadrimestrais; safras recentes sao previsoes. Reproducao autorizada citando a fonte.</div>",
    unsafe_allow_html=True,
)
