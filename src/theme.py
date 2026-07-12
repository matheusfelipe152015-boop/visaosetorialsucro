"""Identidade visual compartilhada do app (mesma da prévia em HTML).

Centraliza tokens de cor/tipografia, o selo de frescor (assinatura do produto),
helpers de card/KPI e o template Plotly. Importado por todas as páginas.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from src.domain.enums import FreshnessStatus
from src.domain.freshness import STATUS_TONE

CANE = "#14573A"
CANE_700 = "#0E3F2A"
AMBER = "#C6881C"
UP = "#1F7A4D"
DOWN = "#B4462E"
INK = "#18241F"
INK_SOFT = "#5C6B63"
LINE = "#E6E2D6"

_TONE_HEX = {"ok": UP, "warn": AMBER, "old": DOWN, "off": "#6B7A74"}

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"], .stApp { font-family:'IBM Plex Sans',system-ui,sans-serif; }
.stApp { background:#FAF8F3; }
h1,h2,h3,h4 { font-family:'Bricolage Grotesque',sans-serif !important; letter-spacing:-.01em; color:#18241F; }
.mono, .mono * { font-family:'IBM Plex Mono',monospace; font-feature-settings:'tnum' 1; }

/* sidebar deep green */
[data-testid="stSidebar"] { background:linear-gradient(180deg,#0E3F2A,#0A2E1F); }
[data-testid="stSidebar"] * { color:#DCE9E1 !important; }
[data-testid="stSidebar"] a { color:#BFD3C8 !important; }

section.main > div { padding-top:1.2rem; }

.eyebrow { font-family:'IBM Plex Mono'; font-size:11px; letter-spacing:.18em;
  text-transform:uppercase; color:#C6881C; font-weight:500; margin-bottom:6px; }

/* cards */
.cv-card { background:#fff; border:1px solid #E6E2D6; border-radius:14px;
  box-shadow:0 10px 30px -22px rgba(20,40,30,.25); padding:16px 18px; margin-bottom:14px; }
.cv-card h3 { font-size:15px; margin:0 0 10px; display:flex; align-items:center; gap:9px; }
.cv-card h3::before { content:""; width:4px; height:15px; border-radius:3px; background:#C6881C; }

/* kpi */
.cv-kpi { background:#fff; border:1px solid #E6E2D6; border-radius:14px; padding:14px 15px;
  box-shadow:0 10px 30px -22px rgba(20,40,30,.25);
  height:100%; min-height:132px; display:flex; flex-direction:column;
  justify-content:space-between; overflow:hidden; }
.cv-kpi .nm { font-size:11.5px; color:#5C6B63; font-weight:600; line-height:1.35;
  display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
  min-height:31px; }
.cv-kpi .un { font-family:'IBM Plex Mono'; font-size:10px; color:#8A968F;
  text-transform:uppercase; letter-spacing:.04em; margin-top:2px; }
.cv-kpi .val { font-family:'IBM Plex Mono'; font-size:23px; font-weight:600;
  letter-spacing:-.02em; white-space:nowrap; line-height:1.15; margin:6px 0 2px; }
.chip { font-family:'IBM Plex Mono'; font-size:12px; font-weight:600; padding:3px 8px;
  border-radius:7px; display:inline-block; }
.chip.up { color:#1F7A4D; background:#E6F2EB; }
.chip.down { color:#B4462E; background:#F6E7E1; }

/* freshness badge — assinatura */
.fresh { display:inline-flex; align-items:center; gap:7px; font-family:'IBM Plex Mono';
  font-size:11px; color:#8A968F; }
.dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
.dot.ok { background:#1F7A4D; box-shadow:0 0 0 3px #E6F2EB; }
.dot.warn { background:#C6881C; box-shadow:0 0 0 3px #FBF3DE; }
.dot.old { background:#B4462E; box-shadow:0 0 0 3px #F6E7E1; }
.dot.off { background:#6B7A74; box-shadow:0 0 0 3px #ECEFED; }

.demobar { background:#FBF3DE; border:1px solid #F0E0BC; color:#7A5A12;
  font-family:'IBM Plex Mono'; font-size:12px; padding:8px 14px; border-radius:10px; margin-bottom:14px; }

.src { font-family:'IBM Plex Mono'; font-size:10px; color:#8A968F; text-transform:uppercase; letter-spacing:.05em; }
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def fresh_badge(status: FreshnessStatus, *, ref: str | None = None) -> str:
    tone = STATUS_TONE.get(status, "off")
    ref_txt = f"&nbsp;· ref {ref}" if ref else ""
    return f'<span class="fresh"><span class="dot {tone}"></span>{status.value}{ref_txt}</span>'


def chip(pct: float) -> str:
    cls = "up" if pct >= 0 else "down"
    arrow = "▲" if pct >= 0 else "▼"
    return f'<span class="chip {cls}">{arrow} {abs(pct):.2f}%</span>'


def plotly_template() -> str:
    pio.templates["canavis"] = go.layout.Template(
        layout=go.Layout(
            font=dict(family="IBM Plex Sans", color=INK, size=12),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=[CANE, AMBER, UP, DOWN, "#6B7A74"],
            xaxis=dict(gridcolor="#EFEBE0", zeroline=False, linecolor=LINE),
            yaxis=dict(gridcolor="#EFEBE0", zeroline=False),
            margin=dict(l=20, r=20, t=20, b=20),
        )
    )
    return "canavis"
