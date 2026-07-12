"""Página 1 — Visão executiva: 'O que mudou no setor desde a última atualização?'"""

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
from src.formato import fmt_indicador, fmt_valor
from src.domain.freshness import freshness_status
from src.persistence.db import fetch_df, init_schema
from src.services.news import PERIODO_DIAS, TODAS, filter_articles
from src.theme import apply_theme, fresh_badge

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Visão executiva", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

# ── cabeçalho ────────────────────────────────────────────────────────────
st.markdown('<div class="eyebrow">Painel diário · America/Sao_Paulo</div>', unsafe_allow_html=True)
st.title("O que mudou no setor")

is_demo = fetch_df("SELECT COUNT(*) c FROM source_runs").iloc[0]["c"] == 0
if is_demo:
    st.markdown(
        '<div class="demobar">⬡ Dados de demonstração (seed). Rode <b>jobs/run_daily.py</b> '
        "para coletar o câmbio real do BCB.</div>",
        unsafe_allow_html=True,
    )

# ── movimentações de mercado (KPIs) ──────────────────────────────────────
st.markdown("##### Movimentações de mercado")
movers = fetch_df(
    """
    SELECT i.code, i.nome, i.unidade, i.frequencia,
           v.valor, v.data_referencia, i.source_code
    FROM indicators i
    JOIN indicator_values v ON v.indicator_code = i.code
    WHERE i.destaque = true
      AND v.data_referencia = (
          SELECT MAX(v2.data_referencia) FROM indicator_values v2
          WHERE v2.indicator_code = i.code)
    ORDER BY i.code
    """
)

POR_LINHA = 4
linhas_kpi = [movers.iloc[i:i + POR_LINHA] for i in range(0, len(movers), POR_LINHA)]
for bloco in linhas_kpi:
    cols = st.columns(POR_LINHA)
    for col, (_, r) in zip(cols, bloco.iterrows(), strict=False):
        ref = date.fromisoformat(str(r["data_referencia"]))
        status = freshness_status(ref, Frequency(r["frequencia"]))
        txt, un = fmt_indicador(r["valor"], r["unidade"])
        with col:
            st.markdown(
                f"""<div class="cv-kpi">
              <div>
                <div class="nm">{r['nome']}</div>
                <div class="un">{un}</div>
              </div>
              <div class="val">{txt}</div>
              <div>{fresh_badge(status, ref=ref.strftime('%d/%m'))}</div>
            </div>""",
                unsafe_allow_html=True,
            )

# ── filtros interativos ──────────────────────────────────────────────────
articles = fetch_df(
    "SELECT id, titulo, data_publicacao, source_code, regiao, segmento FROM news_articles"
)
companies = fetch_df("SELECT code, nome FROM companies")
watch = set(fetch_df("SELECT company_code FROM watchlists")["company_code"])
if not articles.empty:
    mentions = fetch_df("SELECT article_id, company_code FROM article_company_mentions")
    topics_map = fetch_df(
        """SELECT at.article_id, t.nome FROM article_topics at
           JOIN news_topics t ON t.code = at.topic_code"""
    )
else:
    import pandas as _pd
    mentions = _pd.DataFrame(columns=["article_id", "company_code"])
    topics_map = _pd.DataFrame(columns=["article_id", "nome"])
name_by_code = dict(zip(companies["code"], companies["nome"], strict=False))

f1, f2, f3, f4, f5, f6 = st.columns([1.1, 1, 1, 1, 1, 1.2])
periodo = f1.pills("Período", list(PERIODO_DIAS), default="7 dias", key="f_periodo")
regioes = [TODAS] + sorted(x for x in articles["regiao"].dropna().unique())
segmentos = [TODAS] + sorted(x for x in articles["segmento"].dropna().unique())
empresas = [TODAS] + [name_by_code[c] for c in companies["code"]]
fontes = [TODAS] + sorted(articles["source_code"].dropna().unique())
regiao = f2.pills("Região", regioes, default=TODAS, key="f_regiao")
segmento = f3.pills("Segmento", segmentos, default=TODAS, key="f_segmento")
empresa_nome = f4.pills("Empresa", empresas, default=TODAS, key="f_empresa")
fonte = f5.pills("Fonte", fontes, default=TODAS, key="f_fonte")
only_wl = f6.toggle("★ Apenas watchlist", key="f_wl")

empresa_code = next((c for c, n in name_by_code.items() if n == empresa_nome), None)
filt = filter_articles(
    articles, mentions, watch,
    periodo=periodo or "7 dias", regiao=regiao, segmento=segmento,
    empresa=empresa_code, fonte=fonte, only_watchlist=only_wl,
)

st.write("")
left, right = st.columns([1.35, 1])

# ── notícias (filtradas) ─────────────────────────────────────────────────
with left:
    rows = ""
    for _, n in filt.iterrows():
        cos = mentions.loc[mentions["article_id"] == n["id"], "company_code"]
        co_chips = "".join(
            f'<span class="tag co">{name_by_code.get(c, c)}</span>' for c in cos
        )
        tp_chips = "".join(
            f'<span class="tag theme">{t}</span>'
            for t in topics_map.loc[topics_map["article_id"] == n["id"], "nome"]
        )
        rows += (
            f'<div style="padding:11px 0;border-bottom:1px solid #EFEBE0">'
            f'<div style="font-weight:600">{n["titulo"]}</div>'
            f'<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap">{co_chips}{tp_chips}'
            f'<span class="tag">{n["source_code"]}</span></div></div>'
        )
    if not rows:
        rows = '<div class="src" style="padding:14px 0">Nenhuma notícia para os filtros selecionados.</div>'
    aviso_demo = (
        '<div class="demobar" style="margin:6px 0 12px">\u2b21 Not\u00edcias de <b>demonstra\u00e7\u00e3o</b> \u2014 '
        "t\u00edtulos ilustrativos, n\u00e3o s\u00e3o reais. A coleta de not\u00edcias ainda n\u00e3o foi ligada.</div>"
    )
    st.markdown(
        f'<div class="cv-card"><h3>Principais not\u00edcias '
        f'<span class="src">\u00b7 {len(filt)} de {len(articles)}</span></h3>{aviso_demo}{rows}</div>',
        unsafe_allow_html=True,
    )

# ── indicadores em movimento + atenção ───────────────────────────────────
with right:
    ind = fetch_df(
        """
        SELECT i.nome, i.source_code, v.valor
        FROM indicators i JOIN indicator_values v ON v.indicator_code=i.code
        WHERE v.data_referencia=(SELECT MAX(data_referencia) FROM indicator_values
                                 WHERE indicator_code=i.code)
        ORDER BY i.code LIMIT 6
        """
    )
    body = ""
    for _, x in ind.iterrows():
        body += (
            f'<div style="display:flex;justify-content:space-between;padding:10px 0;'
            f'border-bottom:1px solid #EFEBE0"><span style="font-weight:600">{x["nome"]}'
            f'<br><span class="src">{x["source_code"]}</span></span>'
            f'<span class="mono" style="font-weight:600">{fmt_valor(x["valor"])}</span></div>'
        )
    st.markdown(f'<div class="cv-card"><h3>Indicadores em movimento</h3>{body}</div>', unsafe_allow_html=True)

    alerts = fetch_df(
        "SELECT nome, status FROM sources WHERE available = false OR status IN ('Atenção','Desatualizado')"
    )
    a = ""
    for _, s in alerts.iterrows():
        a += (
            f'<div style="display:flex;justify-content:space-between;padding:9px 0;'
            f'border-bottom:1px solid #EFEBE0"><span class="dot off"></span>'
            f'<span style="font-weight:600;flex:1;margin-left:8px">{s["nome"]}</span>'
            f'<span class="src">{s["status"] or "indisponível"}</span></div>'
        )
    st.markdown(
        f'<div class="cv-card"><h3>Requer atenção</h3>{a or "<div class=src>Tudo em dia.</div>"}</div>',
        unsafe_allow_html=True,
    )
