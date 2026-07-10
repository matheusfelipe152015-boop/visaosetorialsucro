"""Página 6 — Clima: chuva por região e estado (mapa interativo do Brasil).

Visão por região (panorama nacional). Ao escolher uma região, o mapa foca nos
estados dela. Dois modos: chuva acumulada (mm) e anomalia vs. média histórica.
Troca de período: semanal, mensal, trimestral.

Fonte prevista: INMET (estações automáticas). Dados de demonstração até a
coleta real ser ligada.
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
from src.services.chuva import REGIOES, anomalia, classifica_anomalia
from src.theme import apply_theme, plotly_template

st.set_page_config(page_title="CANAVIS · Clima", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()
tmpl = plotly_template()

GEOJSON = Path(__file__).resolve().parents[1].parent / "assets" / "geo" / "br_estados.geojson"


@st.cache_data
def carrega_geo() -> dict:
    return json.loads(GEOJSON.read_text(encoding="utf-8"))


st.markdown('<div class="eyebrow">06 · Clima — Chuva</div>', unsafe_allow_html=True)
st.title("Chuva por região e estado")

is_demo = fetch_df(
    "SELECT COUNT(*) c FROM rainfall WHERE collector_version='demo'"
).iloc[0]["c"] > 0
if is_demo:
    st.markdown(
        '<div class="demobar">⬡ Dados de demonstração. A coleta real (INMET) entra na sequência.</div>',
        unsafe_allow_html=True,
    )

# ── controles ────────────────────────────────────────────────────────────
ctrl1, ctrl2, ctrl3 = st.columns([1.2, 1.4, 1])
PERIODOS = {"Semanal": "semanal", "Mensal": "mensal", "Trimestral": "trimestral"}
_seg = getattr(st, "segmented_control", None)
if _seg:
    periodo_lbl = _seg("Período", list(PERIODOS), default="Mensal", label_visibility="collapsed")
    modo = ctrl2.segmented_control(
        "Modo", ["Chuva (mm)", "Anomalia (%)"], default="Chuva (mm)", label_visibility="collapsed"
    )
else:
    periodo_lbl = st.radio("Período", list(PERIODOS), index=1, horizontal=True)
    modo = ctrl2.radio("Modo", ["Chuva (mm)", "Anomalia (%)"], horizontal=True)
periodo_lbl = periodo_lbl or "Mensal"
modo = modo or "Chuva (mm)"
periodo = PERIODOS[periodo_lbl]

foco = ctrl3.selectbox("Região", ["Brasil (todas)", *REGIOES], index=0)

# ── dados do período ─────────────────────────────────────────────────────
dados = fetch_df(
    """SELECT uf, regiao, mm, normal_mm, data_referencia
       FROM rainfall WHERE periodo=:p
       AND data_referencia=(SELECT MAX(data_referencia) FROM rainfall WHERE periodo=:p)""",
    {"p": periodo},
)

if dados.empty:
    st.info("Sem dados de chuva para este período.")
    st.stop()

dados["anomalia"] = dados.apply(lambda r: anomalia(r["mm"], r["normal_mm"]), axis=1)
modo_anomalia = modo.startswith("Anomalia")

# filtra por região se houver foco
geo = carrega_geo()
if foco != "Brasil (todas)":
    dados = dados[dados["regiao"] == foco]
    feats = [f for f in geo["features"] if f["properties"]["regiao"] == foco]
    geo = {"type": "FeatureCollection", "features": feats}

# ── mapa coroplético ─────────────────────────────────────────────────────
if modo_anomalia:
    z = dados["anomalia"]
    escala = [[0, "#B4462E"], [0.5, "#F4F1E9"], [1, "#14573A"]]  # seco -> normal -> chuvoso
    zmid = 0
    titulo_escala = "Anomalia (%)"
else:
    z = dados["mm"]
    escala = [[0, "#F0E0BC"], [0.5, "#6FB28C"], [1, "#0E3F2A"]]  # pouco -> muito (verde-cana)
    zmid = None
    titulo_escala = "Chuva (mm)"

fig = go.Figure(
    go.Choropleth(
        geojson=geo,
        locations=dados["uf"],
        featureidkey="properties.sigla",
        z=z,
        zmid=zmid,
        colorscale=escala,
        marker_line_color="white",
        marker_line_width=0.6,
        colorbar=dict(title=titulo_escala, thickness=12, len=0.7),
        text=dados["uf"],
        customdata=dados[["regiao", "mm", "normal_mm", "anomalia"]],
        hovertemplate=(
            "<b>%{location}</b> (%{customdata[0]})<br>"
            "Chuva: %{customdata[1]:.0f} mm<br>"
            "Normal: %{customdata[2]:.0f} mm<br>"
            "Anomalia: %{customdata[3]:.0f}%<extra></extra>"
        ),
    )
)
fig.update_geos(
    fitbounds="locations",
    visible=False,
    bgcolor="rgba(0,0,0,0)",
    projection_type="mercator",
)
fig.update_layout(template=tmpl, height=520, margin=dict(l=0, r=0, t=10, b=0))
st.plotly_chart(fig, width="stretch")

# ── leitura resumida ─────────────────────────────────────────────────────
if foco == "Brasil (todas)":
    st.markdown("##### Panorama por região")
    from src.services.chuva import chuva_por_regiao

    por_uf = dict(zip(dados["uf"], dados["mm"], strict=False))
    por_uf_norm = dict(zip(dados["uf"], dados["normal_mm"], strict=False))
    reg_mm = chuva_por_regiao(por_uf)
    reg_norm = chuva_por_regiao(por_uf_norm)
    cols = st.columns(len(reg_mm))
    for col, (reg, mm) in zip(cols, reg_mm.items(), strict=False):
        an = anomalia(mm, reg_norm.get(reg, 0))
        cor = "up" if (an or 0) >= 0 else "down"
        col.markdown(
            f'<div class="cv-kpi"><div class="nm">{reg}</div>'
            f'<div class="val">{mm:.0f}<span style="font-size:13px"> mm</span></div>'
            f'<div style="margin-top:6px"><span class="chip {cor}">'
            f'{"+" if (an or 0) >= 0 else ""}{an:.0f}% vs normal</span></div></div>',
            unsafe_allow_html=True,
        )
    st.caption("Dica: escolha uma região no seletor acima para ver os estados em detalhe.")
else:
    st.markdown(f"##### {foco} — estados")
    dd = dados.sort_values("mm", ascending=False)
    rows = ""
    for _, r in dd.iterrows():
        an = r["anomalia"]
        cls = classifica_anomalia(an)
        cor = "up" if (an or 0) >= 0 else "down"
        rows += (
            '<div style="display:flex;align-items:center;gap:12px;padding:10px 0;'
            'border-bottom:1px solid #EFEBE0">'
            f'<div style="font-weight:600;width:48px" class="mono">{r["uf"]}</div>'
            f'<div style="flex:1" class="mono">{r["mm"]:.0f} mm</div>'
            f'<div style="flex:1" class="src">normal {r["normal_mm"]:.0f} mm</div>'
            f'<div style="flex:1.4;text-align:right"><span class="chip {cor}">'
            f'{"+" if (an or 0) >= 0 else ""}{an:.0f}% · {cls}</span></div></div>'
        )
    st.markdown(f'<div class="cv-card">{rows}</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="src" style="margin-top:14px;line-height:1.6">A chuva é determinante para a '
    "moagem e a produtividade da cana. O mapa mostra a precipitação por estado; a anomalia "
    "compara com a média histórica (acima/abaixo do normal). Fonte prevista: INMET.</div>",
    unsafe_allow_html=True,
)
