"""Página 2 — Catálogo de indicadores: tudo o que a plataforma pretende cobrir.

Lista todos os indicadores previstos (mesmo os ainda não coletados), agrupados
por categoria, com fonte, método de coleta, frequência de atualização e cobertura
(com dado real x planejado). É o mapa do que entra na plataforma e de onde vem.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_r = _os.path.abspath(_os.path.dirname(__file__))
while _r != "/" and not _os.path.isdir(_os.path.join(_r, "src")):
    _r = _os.path.dirname(_r)
if _r not in _sys.path:
    _sys.path.insert(0, _r)


from datetime import date

import streamlit as st

from src.app_auth import exigir_login

from src.domain.enums import Frequency
from src.domain.freshness import freshness_status
from src.persistence.db import fetch_df, init_schema
from src.theme import apply_theme, fresh_badge

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Indicadores", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

st.markdown('<div class="eyebrow">02 · Catálogo</div>', unsafe_allow_html=True)
st.title("Indicadores da plataforma")
st.markdown(
    '<div style="color:#5C6B63;max-width:60ch;margin-bottom:8px">Tudo o que pretendemos '
    "acompanhar, com a fonte de origem, o método de coleta e a frequência de atualização. "
    'Itens marcados como <b>planejado</b> ainda não têm coleta ligada.</div>',
    unsafe_allow_html=True,
)

cat = fetch_df(
    """
    SELECT i.code, i.nome, i.categoria, i.unidade, i.frequencia, i.destaque,
           s.nome AS src_nome, s.tier, s.tipo_acesso, s.licenca, s.available,
           MAX(v.data_referencia) AS ref, COUNT(v.id) AS npts
    FROM indicators i
    LEFT JOIN sources s ON s.code = i.source_code
    LEFT JOIN indicator_values v ON v.indicator_code = i.code
    GROUP BY i.code, i.nome, i.categoria, i.unidade, i.frequencia, i.destaque,
             s.nome, s.tier, s.tipo_acesso, s.licenca, s.available
    ORDER BY i.categoria, i.nome
    """
)

# ── resumo ───────────────────────────────────────────────────────────────
total = len(cat)
com_dado = int((cat["npts"] > 0).sum())
planejados = total - com_dado
n_fontes = cat["src_nome"].nunique()
n_cats = cat["categoria"].nunique()

k = st.columns(5)
for col, val, lbl in [
    (k[0], total, "indicadores"),
    (k[1], com_dado, "com dado real"),
    (k[2], planejados, "planejados"),
    (k[3], n_fontes, "fontes"),
    (k[4], n_cats, "categorias"),
]:
    col.markdown(
        f'<div class="cv-kpi"><div class="val">{val}</div>'
        f'<div class="nm">{lbl}</div></div>',
        unsafe_allow_html=True,
    )

st.write("")

# ── filtros ──────────────────────────────────────────────────────────────
cats = ["Todas", *sorted(cat["categoria"].dropna().unique())]
fc1, fc2 = st.columns([3, 1])
sel_cat = fc1.pills("Categoria", cats, default="Todas", key="cat_filter")
so_dado = fc2.toggle("Apenas com dado", key="cat_dado")

view = cat.copy()
if sel_cat and sel_cat != "Todas":
    view = view[view["categoria"] == sel_cat]
if so_dado:
    view = view[view["npts"] > 0]

METODO = {"api": "API", "csv": "CSV/arquivo", "rss": "RSS", "scraping": "scraping", "portal": "portal", "manual": "manual"}
FREQ_LBL = {"daily": "diário", "weekly": "semanal", "biweekly": "quinzenal", "monthly": "mensal", "eventual": "eventual"}


def cobertura(row) -> str:
    if row["npts"] and row["npts"] > 0 and row["ref"]:
        ref = date.fromisoformat(str(row["ref"]))
        status = freshness_status(ref, Frequency(row["frequencia"]), source_available=bool(row["available"]))
        return fresh_badge(status, ref=ref.strftime("%d/%m"))
    return '<span class="fresh"><span class="dot off"></span>planejado</span>'


# ── lista agrupada por categoria ─────────────────────────────────────────
for categoria in [c for c in cats[1:] if (sel_cat in ("Todas", c))]:
    grp = view[view["categoria"] == categoria]
    if grp.empty:
        continue
    rows = ""
    for _, r in grp.iterrows():
        lic = str(r["licenca"] or "")
        lic_chip = (
            f'<span class="tag theme">licença: {lic}</span>'
            if lic in ("a validar", "paga")
            else ""
        )
        star = ' <span class="src" title="Destaque no painel">★</span>' if r["destaque"] else ""
        rows += (
            '<div style="display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid #EFEBE0">'
            f'<div style="flex:1.6;font-weight:600">{r["nome"]}{star}'
            f'<br><span class="src">{r["unidade"] or ""}</span></div>'
            f'<div style="flex:1.4;display:flex;gap:6px;flex-wrap:wrap">'
            f'<span class="tag co">{r["src_nome"] or "—"}</span>'
            f'<span class="tag">Tier {r["tier"] or "—"}</span>{lic_chip}</div>'
            f'<div style="flex:.9" class="src">{METODO.get(r["tipo_acesso"], r["tipo_acesso"] or "—")} · '
            f'{FREQ_LBL.get(r["frequencia"], r["frequencia"] or "—")}</div>'
            f'<div style="flex:.9;text-align:right">{cobertura(r)}</div>'
            "</div>"
        )
    st.markdown(
        f'<div class="cv-card"><h3>{categoria} '
        f'<span class="src">· {len(grp)}</span></h3>{rows}</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="src" style="margin-top:8px;line-height:1.7">★ destaque no painel executivo&nbsp;&nbsp;·&nbsp;&nbsp;'
    '"planejado" = previsto, coleta ainda não ligada&nbsp;&nbsp;·&nbsp;&nbsp;'
    '"licença a validar" = não automatizar até confirmar os termos de uso da fonte.</div>',
    unsafe_allow_html=True,
)
