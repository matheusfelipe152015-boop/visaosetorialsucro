"""Página 7 — Safra: mapa da produção de cana por estado (CONAB).

Mostra onde está a força do setor: produção de cana, açúcar, etanol, área e ATR
por estado, num mapa coroplético do Brasil, safra a safra.

Fonte: CONAB (Portal de Informações Agropecuárias) — dados abertos.
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
from src.safra_visual import (
    carregar_unica,
    fig_acucar_mensal,
    fig_atr,
    fig_atr_chuva_mensal,
    fig_etanol_milho,
    fig_mix,
    fig_moagem,
    fig_moagem_mensal,
    fig_snd_anidro_hidratado,
    fig_snd_atr,
    fig_snd_mensal,
    fig_snd_moagem_mix,
    resumo_safra_atual,
)
from src.theme import apply_theme

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Safra", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

GEOJSON = Path(_r) / "assets" / "geo" / "br_estados.geojson"


@st.cache_data
def carrega_geo() -> dict:
    return json.loads(GEOJSON.read_text(encoding="utf-8"))


METRICAS = {
    "cana_producao": ("Produção de cana", "mil t", [[0, "#F0E0BC"], [0.5, "#6FB28C"], [1, "#0E3F2A"]]),
    "acucar_producao": ("Produção de açúcar", "mil t", [[0, "#FBF3E0"], [0.5, "#E0B457"], [1, "#8A5D0F"]]),
    "etanol_producao": ("Produção de etanol", "mil L", [[0, "#E8F0EC"], [0.5, "#5FA37C"], [1, "#14573A"]]),
    "cana_area_plantada": ("Área plantada", "mil ha", [[0, "#EFEBE0"], [0.5, "#9BB09F"], [1, "#2E4A38"]]),
    "cana_atr_medio": ("ATR médio", "kg/t", [[0, "#F4F1E9"], [0.5, "#C6881C"], [1, "#7A4E08"]]),
}

st.markdown('<div class="eyebrow">07 · Safra — produção por estado</div>', unsafe_allow_html=True)
st.title("Mapa da safra")

# ══ UNICA — moagem, mix e ATR do Centro-Sul ═══════════════════════════════


def _sec_safra(titulo: str, sub: str = "") -> None:
    linha_sub = (f'<div style="font-size:13px;color:#5C6B63;margin-top:2px">{sub}</div>'
                 if sub else "")
    st.markdown(
        f'<div style="margin:14px 0 8px"><div style="font-size:16px;font-weight:800;'
        f'color:#18241F">{titulo}</div>{linha_sub}<div style="height:2px;'
        f'background:#14573A;width:40px;margin-top:6px;border-radius:2px"></div></div>',
        unsafe_allow_html=True)


try:
    _unica = carregar_unica()
except Exception:  # noqa: BLE001 — se o download falhar, segue com o mapa
    _unica = None

if _unica is not None and not _unica.empty:
    _sec_safra("Centro-Sul — UNICA", "moagem, mix e ATR por safra (acumulado)")
    _r = resumo_safra_atual(_unica)
    if _r:
        _cana = f"{_r['cana_mil_t'] / 1000:,.1f} mi t".replace(",", ".")
        _ac = f"{_r['acucar_mil_t'] / 1000:,.1f} mi t".replace(",", ".")
        _et = f"{_r['etanol_mil_m3'] / 1000:,.1f} mi m³".replace(",", ".")
        _cards = [
            ("Safra", str(_r["safra"]), ""),
            ("Cana moída", _cana, "acumulado"),
            ("Açúcar", _ac, "acumulado"),
            ("Etanol", _et, "acumulado"),
            ("ATR médio", f"{_r['atr']:.1f} kg/t".replace(".", ","), ""),
            ("Mix açúcar", f"{_r['mix_acucar']:.1f}%".replace(".", ","), "do ATR"),
        ]
        _html = '<div style="display:flex;gap:12px;flex-wrap:wrap;margin:4px 0 14px">'
        for _rot, _val, _sub in _cards:
            _html += (f'<div style="flex:1;min-width:130px;background:#fff;'
                      f'border:1px solid #E6E2D6;border-radius:12px;padding:12px 14px">'
                      f'<div style="font-size:11px;letter-spacing:.06em;'
                      f'text-transform:uppercase;color:#5C6B63">{_rot}</div>'
                      f'<div style="font-size:19px;font-weight:800;color:#18241F;'
                      f'margin-top:3px">{_val}</div>'
                      f'<div style="font-size:11px;color:#5C6B63">{_sub}</div></div>')
        _html += "</div>"
        st.markdown(_html, unsafe_allow_html=True)

    _c1, _c2, _c3 = st.columns(3)
    with _c1:
        st.markdown("**Cana moída por safra**")
        _f = fig_moagem(_unica)
        if _f:
            st.plotly_chart(_f, width="stretch")
    with _c2:
        st.markdown("**Mix açúcar × etanol**")
        _f = fig_mix(_unica)
        if _f:
            st.plotly_chart(_f, width="stretch")
    with _c3:
        st.markdown("**ATR médio**")
        _f = fig_atr(_unica)
        if _f:
            st.plotly_chart(_f, width="stretch")

    st.markdown('<div class="src" style="margin:4px 0 8px">Fonte: UNICA — '
                'compilado por sugar-intel (dados abertos).</div>',
                unsafe_allow_html=True)
    st.divider()

_sec_safra("Safra mês a mês", "moagem, mix, açúcar e ATR do Centro-Sul (UNICA)")
_m1, _m2 = st.columns(2)
with _m1:
    st.markdown("**Cana moída e mix de açúcar**")
    _f = fig_moagem_mensal()
    if _f:
        st.plotly_chart(_f, width="stretch")
    else:
        st.caption("Rode o coletor unica_snd para preencher.")
with _m2:
    st.markdown("**ATR médio e chuva no Centro-Sul**")
    _f = fig_atr_chuva_mensal()
    if _f:
        st.plotly_chart(_f, width="stretch")

st.markdown("**Produção mensal de açúcar**")
_f = fig_acucar_mensal()
if _f:
    st.plotly_chart(_f, width="stretch")

_sec_safra("Etanol — oferta × demanda mensal",
           "Centro-Sul: produção vs vendas e o estoque acumulado (UNICA)")
_f = fig_snd_mensal()
if _f:
    st.plotly_chart(_f, width="stretch")
else:
    st.caption("Rode o coletor unica_snd para preencher.")

_sec_safra("Moagem e mix mês a mês", "cana moída, açúcar produzido e o mix (UNICA)")
_f = fig_snd_moagem_mix()
if _f:
    st.plotly_chart(_f, width="stretch")

_m1, _m2 = st.columns(2)
with _m1:
    st.markdown("**Produção de etanol por tipo**")
    _f = fig_snd_anidro_hidratado()
    if _f:
        st.plotly_chart(_f, width="stretch")
with _m2:
    st.markdown("**ATR médio mensal**")
    _f = fig_snd_atr()
    if _f:
        st.plotly_chart(_f, width="stretch")

_sec_safra("Etanol de milho — Brasil", "produção por safra (CONAB)")
_f = fig_etanol_milho()
if _f:
    st.plotly_chart(_f, width="stretch")
else:
    st.caption("Rode o coletor de etanol de milho para preencher.")

st.divider()
st.markdown('<div class="eyebrow">Mapa por estado — CONAB</div>', unsafe_allow_html=True)

dados_todos = fetch_df(
    "SELECT uf, regiao, safra, metric, valor, unidade FROM safra_uf WHERE source_code = 'conab'"
)

if dados_todos.empty:
    st.info("Sem dados de safra ainda. Rode `python jobs/run_daily.py` para coletar da CONAB.")
    st.stop()

# ── controles ────────────────────────────────────────────────────────────
c1, c2 = st.columns([1, 1])
safras = sorted(dados_todos["safra"].unique(), reverse=True)
safra = c1.selectbox("Safra", safras, index=0)
metrica_nome = c2.selectbox(
    "Indicador", [v[0] for v in METRICAS.values()], index=0
)
metrica = next(k for k, v in METRICAS.items() if v[0] == metrica_nome)
label, unidade, escala = METRICAS[metrica]

dados = dados_todos[
    (dados_todos["safra"] == safra) & (dados_todos["metric"] == metrica)
].copy()

if dados.empty:
    st.warning("Sem dados para essa combinação.")
    st.stop()

geo = carrega_geo()

# ── KPIs do topo ─────────────────────────────────────────────────────────
total = dados["valor"].sum()
lider = dados.loc[dados["valor"].idxmax()]
k1, k2, k3 = st.columns(3)
agregado = "média" if metrica == "cana_atr_medio" else "total"
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
    f'<div class="cv-kpi"><div class="nm">Estados com produção</div>'
    f'<div class="val">{len(dados)}</div>'
    f'<div style="margin-top:6px"><span class="src">na safra {safra}</span></div></div>',
    unsafe_allow_html=True,
)

# ── mapa coroplético ─────────────────────────────────────────────────────
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
            f"{label}: " + "%{z:,.1f} " + unidade + "<extra></extra>"
        ),
    )
)
fig.update_geos(fitbounds="locations", visible=False)
fig.update_layout(
    margin=dict(l=0, r=0, t=10, b=0), height=520,
    paper_bgcolor="rgba(0,0,0,0)", geo_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

# ── ranking dos estados ──────────────────────────────────────────────────
st.markdown("##### Todos os estados")
rank = dados.sort_values("valor", ascending=False)[["uf", "regiao", "valor"]].copy()
rank["valor"] = rank["valor"].round(1)
rank.columns = ["UF", "Região", f"{label} ({unidade})"]
st.dataframe(rank.set_index("UF"), width="stretch")

st.markdown(
    '<div class="src" style="margin-top:14px;line-height:1.6">Fonte: CONAB — Portal de '
    "Informações Agropecuárias, Série Histórica da Cana-de-açúcar. Levantamentos "
    "quadrimestrais; safras recentes são previsões. Reprodução autorizada citando a fonte.</div>",
    unsafe_allow_html=True,
)
