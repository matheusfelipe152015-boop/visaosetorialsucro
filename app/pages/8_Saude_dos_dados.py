"""Página 8 — Saúde dos dados: situação de cada fonte e indicador."""

from __future__ import annotations

import os as _os
import sys as _sys

_r = _os.path.abspath(_os.path.dirname(__file__))
while _r != "/" and not _os.path.isdir(_os.path.join(_r, "src")):
    _r = _os.path.dirname(_r)
if _r not in _sys.path:
    _sys.path.insert(0, _r)


import pandas as pd

from datetime import date

import streamlit as st

from src.app_auth import exigir_login

from src.domain.enums import Frequency
from src.domain.freshness import freshness_status
from src.persistence.db import fetch_df, init_schema
from src.theme import apply_theme, fresh_badge


def _num(v) -> int:
    """Converte para int com segurança (None e NaN viram 0)."""
    try:
        if v is None or v != v:
            return 0
        return int(v)
    except (TypeError, ValueError):
        return 0

st.set_page_config(page_title="CANAVIS · Saúde dos dados", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

st.markdown('<div class="eyebrow">08 · Técnico</div>', unsafe_allow_html=True)
st.title("Saúde dos dados")

runs = fetch_df(
    """SELECT s.code, s.nome, s.tier, s.frequencia_esperada, s.available,
              r.finished_at, r.rows_seen, r.rows_new, r.duration_s, r.ok, r.error
       FROM sources s
       LEFT JOIN source_runs r ON r.id = (
           SELECT id FROM source_runs WHERE source_code=s.code
           ORDER BY finished_at DESC LIMIT 1)
       ORDER BY s.tier, s.code"""
)

if runs.empty:
    st.info("Nenhuma fonte cadastrada ainda. Rode o seed.")
    st.stop()

for _, s in runs.iterrows():
    ind = fetch_df(
        """SELECT MAX(data_referencia) ref FROM indicator_values WHERE source_code=:s""",
        {"s": s["code"]},
    ).iloc[0]["ref"]
    freq = Frequency(s["frequencia_esperada"] or "unknown")
    ref_date = date.fromisoformat(str(ind)) if ind else None
    status = freshness_status(ref_date, freq, source_available=bool(s["available"]))
    last_run = str(s["finished_at"])[:16] if s["finished_at"] else "—"
    err = f' · <span class="src" style="color:#B4462E">{s["error"]}</span>' if s["error"] else ""
    st.markdown(
        f"""<div class="cv-card" style="display:flex;justify-content:space-between;align-items:center">
          <div><b>{s['nome']}</b> <span class="src">Tier {s['tier'] or '—'} · {freq.value}</span><br>
            <span class="src">última execução {last_run} · {int(pd.notna(s['rows_seen']) and s['rows_seen'] or 0)} lidos / {int(pd.notna(s['rows_new']) and s['rows_new'] or 0)} novos{err}</span></div>
          <div>{fresh_badge(status, ref=ref_date.strftime('%d/%m') if ref_date else None)}</div>
        </div>""",
        unsafe_allow_html=True,
    )
