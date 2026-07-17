"""Página 4 — Preços por estado: mapa de combustíveis e paridade etanol/gasolina.

O destaque é a PARIDADE: etanol ÷ gasolina, em %. Abaixo de ~70%, compensa
abastecer com etanol (rende menos por litro, mas sai mais barato no bolso).
Acima disso, o consumidor migra para gasolina — e a demanda de etanol cai.
Para crédito: usina em estado onde o etanol não compete tende a ter demanda
mais fraca no mercado interno.

Fonte: ANP — Série Histórica de Preços de Combustíveis (dados abertos).
"""

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

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Preços por estado", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

GEOJSON = Path(_r) / "assets" / "geo" / "br_estados.geojson"
LIMITE_PARIDADE = 70.0  # abaixo disso, o etanol compensa


@st.cache_data
def carrega_geo() -> dict:
    return json.loads(GEOJSON.read_text(encoding="utf-8"))


st.markdown('<div class="eyebrow">04 · Preços — combustíveis por estado</div>', unsafe_allow_html=True)
st.title("Mapa de preços e paridade")

dados_todos = fetch_df(
    "SELECT uf, regiao, periodo, metric, valor, unidade FROM metricas_uf WHERE source_code = 'anp'"
)

if dados_todos.empty:
    st.info("Sem preços por estado ainda. Rode `python3.12 jobs/run_daily.py` para coletar da ANP.")
    st.stop()

METRICAS = {
    "paridade_etanol": "Paridade etanol/gasolina",
    "preco_etanol": "Preço do etanol",
    "preco_gasolina": "Preço da gasolina",
}

c1, c2 = st.columns([1, 1])
periodos = sorted(dados_todos["periodo"].unique(), reverse=True)
periodo = c1.selectbox("Período", periodos, index=0)
disponiveis = [
    METRICAS[m] for m in METRICAS if m in set(dados_todos["metric"])
]
metrica_nome = c2.selectbox("Indicador", disponiveis, index=0)
metrica = next(k for k, v in METRICAS.items() if v == metrica_nome)

dados = dados_todos[
    (dados_todos["periodo"] == periodo) & (dados_todos["metric"] == metrica)
].copy()
if dados.empty:
    st.warning("Sem dados para essa combinação.")
    st.stop()

geo = carrega_geo()
eh_paridade = metrica == "paridade_etanol"
unidade = "%" if eh_paridade else "R$/L"

# ── leitura de topo ──────────────────────────────────────────────────────
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
        f'<div class="cv-kpi"><div class="nm">Paridade média do país</div>'
        f'<div class="val">{media:,.1f}<span style="font-size:13px"> %</span></div>'
        f'<div style="margin-top:6px"><span class="src">etanol ÷ gasolina</span></div></div>',
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
        "a gasolina tende a levar a preferência — e a demanda de etanol enfraquece.</div>",
        unsafe_allow_html=True,
    )
else:
    media = dados["valor"].mean()
    caro = dados.loc[dados["valor"].idxmax()]
    barato = dados.loc[dados["valor"].idxmin()]
    k1, k2, k3 = st.columns(3)
    k1.markdown(
        f'<div class="cv-kpi"><div class="nm">Média do país</div>'
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

# ── mapa ─────────────────────────────────────────────────────────────────
if eh_paridade:
    # verde = etanol compensa (baixo) | vermelho = não compensa (alto)
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

# ── ranking ──────────────────────────────────────────────────────────────
st.markdown("##### Todos os estados")
asc = eh_paridade  # paridade: menor é melhor (etanol compete)
rank = dados.sort_values("valor", ascending=asc)[["uf", "regiao", "valor"]].copy()
rank["valor"] = rank["valor"].round(1 if eh_paridade else 2)
if eh_paridade:
    rank["situação"] = rank["valor"].map(
        lambda v: "✓ etanol compensa" if v < LIMITE_PARIDADE else "gasolina leva"
    )
rank = rank.rename(columns={"uf": "UF", "regiao": "Região", "valor": f"{metrica_nome} ({unidade})"})
st.dataframe(rank.set_index("UF"), width="stretch")

st.markdown(
    '<div class="src" style="margin-top:14px;line-height:1.6">Fonte: ANP — Série Histórica de '
    "Preços de Combustíveis (levantamento em postos de revenda). A paridade é calculada pela "
    "plataforma: preço médio do etanol dividido pelo preço médio da gasolina comum, por estado. "
    "Médias do período; variações locais existem.</div>",
    unsafe_allow_html=True,
)
