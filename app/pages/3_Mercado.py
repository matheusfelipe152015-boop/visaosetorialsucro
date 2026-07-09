"""Página 3 — Mercado (câmbio USD/BRL via BCB PTAX)."""

from __future__ import annotations

from datetime import date

import plotly.graph_objects as go
import streamlit as st

from src.domain.enums import Frequency
from src.domain.freshness import freshness_status
from src.persistence.db import fetch_df, init_schema
from src.theme import CANE, apply_theme, chip, fresh_badge, plotly_template

st.set_page_config(page_title="CANAVIS · Mercado", page_icon="⬡", layout="wide")
init_schema()
apply_theme()
tmpl = plotly_template()

st.markdown('<div class="eyebrow">03 · Mercado — Câmbio</div>', unsafe_allow_html=True)
st.title("Dólar comercial")

df = fetch_df(
    """SELECT data_referencia, valor, unidade, data_coleta, source_code
       FROM indicator_values WHERE indicator_code='usd_brl'
       ORDER BY data_referencia"""
)

if df.empty:
    st.info("Sem dados ainda. Rode `python jobs/run_daily.py` ou `python db/seeds/seed_demo.py`.")
    st.stop()

df["data_referencia"] = df["data_referencia"].astype(str)
last = df.iloc[-1]
ref = date.fromisoformat(last["data_referencia"])
status = freshness_status(ref, Frequency.DAILY)


def pct_change(days_back: int) -> float | None:
    if len(df) <= days_back:
        return None
    prev = df.iloc[-1 - days_back]["valor"]
    return (last["valor"] / prev - 1) * 100 if prev else None


# ── topo: valor atual + variações ────────────────────────────────────────
c1, c2 = st.columns([1, 1])
with c1:
    st.markdown(
        f'<div class="mono" style="font-size:42px;font-weight:600;letter-spacing:-.02em">'
        f'{last["valor"]:.4f}</div>'
        f'<div style="margin-top:6px">{fresh_badge(status, ref=ref.strftime("%d/%m/%Y"))}</div>',
        unsafe_allow_html=True,
    )
with c2:
    chips = ""
    for lbl, d in [("Diário", 1), ("Semana", 5), ("Mês", 22), ("Ano", 252)]:
        p = pct_change(d)
        chips += f'<div style="display:inline-block;margin:0 14px 8px 0"><span class="src">{lbl}</span><br>{chip(p) if p is not None else "—"}</div>'
    st.markdown(chips, unsafe_allow_html=True)

# ── seletor de janela do gráfico (interativo) ────────────────────────────
WINDOWS = {"7D": 7, "1M": 30, "3M": 90, "1A": 365, "Máx": 10_000}
_seg = getattr(st, "segmented_control", None)
if _seg is not None:
    win = _seg("Janela", list(WINDOWS), default="3M", label_visibility="collapsed")
else:  # fallback p/ versões mais antigas do Streamlit
    win = st.radio("Janela", list(WINDOWS), index=2, horizontal=True, label_visibility="collapsed")
win = win or "3M"

import pandas as pd  # noqa: E402

_dt = pd.to_datetime(df["data_referencia"])
cutoff = _dt.max() - pd.Timedelta(days=WINDOWS[win])
dff = df[_dt >= cutoff] if WINDOWS[win] < 10_000 else df
if len(dff) >= 2:
    win_pct = (dff.iloc[-1]["valor"] / dff.iloc[0]["valor"] - 1) * 100
    st.markdown(f"Variação no período ({win}): {chip(win_pct)}", unsafe_allow_html=True)

# ── gráfico ──────────────────────────────────────────────────────────────
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=dff["data_referencia"],
        y=dff["valor"],
        mode="lines",
        line=dict(color=CANE, width=2.2),
        fill="tozeroy",
        fillcolor="rgba(20,87,58,0.08)",
        name="USD/BRL",
    )
)
fig.update_layout(template=tmpl, height=340, showlegend=False)
fig.update_yaxes(range=[dff["valor"].min() * 0.98, dff["valor"].max() * 1.02])
st.plotly_chart(fig, width="stretch")

# ── faixa de metadados (rastreabilidade) ─────────────────────────────────
m = st.columns(6)
meta = [
    ("Último valor", f'{last["valor"]:.4f}'),
    ("Unidade", last["unidade"]),
    ("Data de referência", ref.strftime("%d/%m/%Y")),
    ("Última coleta", str(last["data_coleta"])[:16]),
    ("Fonte", "BCB · SGS 1"),
    ("Status", status.value),
]
for col, (k, v) in zip(m, meta, strict=False):
    col.markdown(f'<span class="src">{k}</span><br><b>{v}</b>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════
# SEÇÃO 2 — COMBUSTÍVEIS (ANP) + PARIDADE ETANOL/GASOLINA
# ═══════════════════════════════════════════════════════════════════════
from src.services.paridade import LIMITE_VANTAGEM, leitura_paridade, paridade  # noqa: E402

st.write("")
st.markdown('<div class="eyebrow">03 · Mercado — Combustíveis</div>', unsafe_allow_html=True)
st.title("Combustíveis e paridade")


def _ultimo(code: str):
    d = fetch_df(
        """SELECT valor, data_referencia FROM indicator_values
           WHERE indicator_code=:c ORDER BY data_referencia DESC LIMIT 1""",
        {"c": code},
    )
    return (d.iloc[0]["valor"], d.iloc[0]["data_referencia"]) if not d.empty else (None, None)


gas_v, gas_ref = _ultimo("preco_gasolina")
eta_v, eta_ref = _ultimo("preco_etanol")

if gas_v is None or eta_v is None:
    st.info("Sem preços de combustível ainda. Rode a coleta da ANP (`python jobs/run_daily.py`).")
else:
    par = paridade(eta_v, gas_v)
    par_pct = par * 100
    compensa = par < LIMITE_VANTAGEM
    cor = "up" if compensa else "down"
    ref_fuel = date.fromisoformat(str(eta_ref))
    status_fuel = freshness_status(ref_fuel, Frequency.WEEKLY)

    fc1, fc2, fc3 = st.columns(3)
    fc1.markdown(
        f'<div class="cv-kpi"><div class="nm">Gasolina comum</div>'
        f'<div class="val">R$ {gas_v:.3f}</div>'
        f'<div style="margin-top:6px"><span class="src">ANP · revenda</span></div></div>',
        unsafe_allow_html=True,
    )
    fc2.markdown(
        f'<div class="cv-kpi"><div class="nm">Etanol hidratado</div>'
        f'<div class="val">R$ {eta_v:.3f}</div>'
        f'<div style="margin-top:6px"><span class="src">ANP · revenda</span></div></div>',
        unsafe_allow_html=True,
    )
    fc3.markdown(
        f'<div class="cv-kpi" style="outline:1.5px solid var(--cane-300);outline-offset:-1.5px">'
        f'<div class="nm">Paridade etanol/gasolina</div>'
        f'<div class="val">{par_pct:.1f}%</div>'
        f'<div style="margin-top:6px"><span class="chip {cor}">'
        f'{"etanol compensa" if compensa else "gasolina compensa"}</span></div></div>',
        unsafe_allow_html=True,
    )

    # barra visual da paridade com a marca dos 70%
    pos = min(par_pct, 100)
    barra_cor = "#1F7A4D" if compensa else "#B4462E"
    st.markdown(
        f"""
        <div style="margin:20px 0 6px;position:relative;height:38px">
          <div style="position:absolute;top:14px;left:0;right:0;height:10px;border-radius:6px;
               background:linear-gradient(90deg,#E6F2EB,#FBF3DE 70%,#F6E7E1)"></div>
          <div style="position:absolute;top:9px;left:70%;width:2px;height:20px;background:#18241F"></div>
          <div style="position:absolute;top:-4px;left:70%;transform:translateX(-50%);
               font-family:'IBM Plex Mono';font-size:10px;color:#5C6B63">70%</div>
          <div style="position:absolute;top:10px;left:{pos}%;transform:translateX(-50%);
               width:18px;height:18px;border-radius:50%;background:{barra_cor};
               border:3px solid #fff;box-shadow:0 2px 6px rgba(0,0,0,.2)"></div>
        </div>
        <div class="src" style="text-align:center">
          {leitura_paridade(eta_v, gas_v)} &nbsp;·&nbsp; {fresh_badge(status_fuel, ref=ref_fuel.strftime("%d/%m"))}
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="src" style="margin-top:14px;line-height:1.6">A paridade compara o preço do '
        "etanol com o da gasolina. Abaixo de 70%, o etanol tende a compensar para o consumidor — "
        "o que sustenta a demanda por etanol e, por consequência, o setor sucroenergético. "
        "Preços médios nacionais de revenda (ANP).</div>",
        unsafe_allow_html=True,
    )
