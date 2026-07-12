"""Pagina 4 — Precos por estado: mapa de combustiveis e paridade etanol/gasolina."""

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

st.set_page_config(page_title="CANAVIS · Precos por estado", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

GEOJSON = Path(_r) / "assets" / "geo" / "br_estados.geojson"
LIMITE_PARIDADE = 70.0


@st.cache_data
def carrega_geo():
    return json.loads(GEOJSON.read_text(encoding="utf-8"))


st.markdown('<div class="eyebrow">04 · Precos — combustiveis por estado</div>', unsafe_allow_html=True)
st.title("Mapa de precos e paridade")

dados_todos = fetch_df(
    "SELECT uf, regiao, periodo, metric, valor, unidade FROM metricas_uf WHERE source_code = 'anp'"
)

if dados_todos.empty:
    st.info("Sem precos por estado ainda. Rode `python3.12 jobs/run_daily.py` para coletar da ANP.")
    st.stop()

METRICAS = {
    "paridade_etanol": "Paridade etanol/gasolina",
    "preco_etanol": "Preco do etanol",
    "preco_gasolina": "Preco da gasolina",
}

c1, c2 = st.columns([1, 1])
periodos = sorted(dados_todos["periodo"].unique(), reverse=True)
periodo = c1.selectbox("Periodo", periodos, index=0)
disponiveis = [METRICAS[m] for m in METRICAS if m in set(dados_todos["metric"])]
metrica_nome = c2.selectbox("Indicador", disponiveis, index=0)
metrica = next(k for k, v in METRICAS.items() if v == metrica_nome)

dados = dados_todos[
    (dados_todos["periodo"] == periodo) & (dados_todos["metric"] == metrica)
].copy()
if dados.empty:
    st.warning("Sem dados para essa combinacao.")
    st.stop()

geo = carrega_geo()
eh_paridade = metrica == "paridade_etanol"
unidade = "%" if eh_paridade else "R$/L"

if eh_paridade:
    compensa = dados[dados["valor"] < LIMITE_PARIDADE]
    media = dados["valor"].mean()
    melhor = dados.loc[dados["valor"].idxmin()]
    k1, k2, k3 = st.columns(3)
    k1.markdown(
        f'<div class="cv-kpi"><div class="nm">Estados onde o etanol compensa</div>'
        f'<div class="val">{len(compensa)}<span style="font-size:13px"> de {len(dados)}</span></div>'
        f'<div style="margin-top:6px"><span class="src">paridade abaixo de {LIMITE_PARIDADE:.0f}%</span></div></div>',
        unsafe_allow_html=True,
    )
    k2.markdown(
        f'<div class="cv-kpi"><div class="nm">Paridade media do pais</div>'
        f'<div class="val">{media:,.1f}<span style="font-size:13px"> %</span></div>'
        f'<div style="margin-top:6px"><span class="src">etanol / gasolina</span></div></div>',
        unsafe_allow_html=True,
    )
    k3.markdown(
        f'<div class="cv-kpi"><div class="nm">Etanol mais competitivo</div>'
        f'<div class="val">{melhor["uf"]}</div>'
        f'<div style="margin-top:6px"><span class="src">paridade {melhor["valor"]:,.1f}%</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="src" style="margin:10px 0 4px">Regra de bolso do setor: abaixo de '
        f"<b>{LIMITE_PARIDADE:.0f}%</b> o etanol compensa no bolso do consumidor; acima disso, "
        "a gasolina tende a levar a preferencia — e a demanda de etanol enfraquece.</div>",
        unsafe_allow_html=True,
    )
else:
    media = dados["valor"].mean()
    caro = dados.loc[dados["valor"].idxmax()]
    barato = dados.loc[dados["valor"].idxmin()]
    k1, k2, k3 = st.columns(3)
    k1.markdown(
        f'<div class="cv-kpi"><div class="nm">Media do pais</div>'
        f'<div class="val">{media:,.2f}<span style="font-size:13px"> R$/L</span></div>'
        f'<div style="margin-top:6px"><span class="src">{periodo}</span></div></div>',
        unsafe_allow_html=True,
    )
    k2.markdown(
        f'<div class="cv-kpi"><div class="nm">Mais caro</div>'
        f'<div class="val">{caro["uf"]}</div>'
        f'<div style="margin-top:6px"><span class="src">R$ {caro["valor"]:,.2f}/L</span></div></div>',
        unsafe_allow_html=True,
    )
    k3.markdown(
        f'<div class="cv-kpi"><div class="nm">Mais barato</div>'
        f'<div class="val">{barato["uf"]}</div>'
        f'<div style="margin-top:6px"><span class="src">R$ {barato["valor"]:,.2f}/L</span></div></div>',
        unsafe_allow_html=True,
    )

if eh_paridade:
    escala = [[0, "#14573A"], [0.5, "#E0B457"], [1, "#B4462E"]]
    zmin, zmax = 55, 95
    titulo = "Paridade (%)"
else:
    escala = [[0, "#F0E0BC"], [0.5, "#6FB28C"], [1, "#0E3F2A"]]
    zmin = zmax = None
    titulo = "R$/L"

fig = go.Figure(
    go.Choropleth(
        geojson=geo,
        locations=dados["uf"],
        featureidkey="properties.sigla",
        z=dados["valor"],
        zmin=zmin,
        zmax=zmax,
        colorscale=escala,
        marker_line_color="white",
        marker_line_width=0.6,
        colorbar=dict(title=titulo, thickness=12, len=0.7),
        customdata=dados[["regiao"]],
        hovertemplate=(
            "<b>%{location}</b> (%{customdata[0]})<br>"
            + metrica_nome + ": %{z:,.1f} " + unidade + "<extra></extra>"
        ),
    )
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin=dict(l=0, r=0, t=10, b=0), height=520,
    paper_bgcolor="rgba(0,0,0,0)", geo_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

st.markdown("##### Por estado")
asc = eh_paridade
rank = dados.sort_values("valor", ascending=asc)[["uf", "regiao", "valor"]].head(12)
if eh_paridade:
    rank["situacao"] = rank["valor"].map(
        lambda v: "etanol compensa" if v < LIMITE_PARIDADE else "gasolina leva"
    )
rank = rank.rename(columns={"uf": "UF", "regiao": "Regiao", "valor": f"{metrica_nome} ({unidade})"})
st.dataframe(rank.set_index("UF"), width="stretch")

st.markdown(
    '<div class="src" style="margin-top:14px;line-height:1.6">Fonte: ANP — Serie Historica de '
    "Precos de Combustiveis (postos de revenda). A paridade e calculada pela plataforma: preco "
    "medio do etanol dividido pelo preco medio da gasolina comum, por estado.</div>",
    unsafe_allow_html=True,
)
