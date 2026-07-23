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
from src.indicadores_visual import kpi_indicadores, serie_para_grafico
from src.persistence.db import fetch_df, init_schema
from src.theme import apply_theme, fresh_badge

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Indicadores", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

st.markdown('<div class="eyebrow">02 · Catálogo</div>', unsafe_allow_html=True)
st.title("Indicadores da plataforma")

# ── PAINEL DE MERCADO (estilo painel de preços) ──────────────────────────
import plotly.express as _px  # noqa: E402

_SECOES = {
    "Açúcar": [
        ("sugar_ny11", "Açúcar NY nº 11", "¢/lb"),
        ("acucar_cristal_sp", "Cristal ESALQ (SP)", "R$/sc"),
        ("acucar_londres5", "Branco Londres nº 5", "US$/t"),
    ],
    "Etanol": [
        ("etanol_hidratado", "Hidratado (SP)", "R$/L"),
        ("etanol_anidro_sp", "Anidro (SP)", "R$/L"),
        ("preco_etanol", "Etanol revenda", "R$/L"),
    ],
    "Petróleo & câmbio": [
        ("brent", "Brent", "US$/bbl"),
        ("wti", "WTI", "US$/bbl"),
        ("usd_brl", "USD/BRL", "R$"),
        ("selic_meta", "Selic meta", "% a.a."),
    ],
}

st.markdown(
    '<div style="color:#5C6B63;max-width:70ch;margin-bottom:6px">Painel de '
    "mercado do complexo sucroenergético — valor mais recente e variações "
    "em 30 dias, 90 dias e 12 meses. Fontes citadas no catálogo abaixo.</div>",
    unsafe_allow_html=True,
)

for titulo, itens in _SECOES.items():
    st.markdown(
        f'<div style="font-size:15px;font-weight:800;color:#18241F;'
        f'margin:14px 0 2px">{titulo}</div>'
        f'<div style="height:2px;background:#14573A;width:38px;'
        f'border-radius:2px;margin-bottom:8px"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(kpi_indicadores(itens), unsafe_allow_html=True)

# gráficos de histórico — todos na tela, 2 por linha (sem escolher)
st.markdown(
    '<div style="font-size:15px;font-weight:800;color:#18241F;margin:16px 0 6px">'
    "Histórico</div>", unsafe_allow_html=True,
)
_todos = [(c, n) for sec in _SECOES.values() for (c, n, _u) in sec]
_com_dado = []
for _code, _nome in _todos:
    _s = serie_para_grafico(_code, dias=365)
    if not _s.empty:
        _com_dado.append((_nome, _s))

if not _com_dado:
    st.caption("Ainda não há histórico coletado para estes indicadores.")
else:
    for _i in range(0, len(_com_dado), 2):
        _cols = st.columns(2)
        for _j, (_nome, _s) in enumerate(_com_dado[_i:_i + 2]):
            with _cols[_j]:
                st.markdown(f'<div style="font-size:13px;font-weight:700;'
                            f'color:#18241F;margin-bottom:2px">{_nome}</div>',
                            unsafe_allow_html=True)
                _fig = _px.line(_s, x="Data", y="Valor",
                                color_discrete_sequence=["#14573A"])
                _fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",
                                   plot_bgcolor="rgba(0,0,0,0)", height=240,
                                   margin=dict(l=10, r=10, t=6, b=10),
                                   xaxis_title="", yaxis_title="")
                st.plotly_chart(_fig, width="stretch",
                                key=f"hist_{_i}_{_j}")

st.divider()
st.markdown('<div class="eyebrow">Catálogo completo</div>', unsafe_allow_html=True)
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
