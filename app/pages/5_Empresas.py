"""Página 5 — Empresas: visão das usinas de capital aberto.

Centraliza os dados operacionais (moagem, mix, ATR, produção) que as usinas
divulgam em seus releases/DFs, evitando entrar "RI por RI". Mostra:
  - leitura agregada do setor (moagem subindo/caindo, mix médio);
  - cards por empresa (resumo executivo operacional);
  - comparação lado a lado.

Fontes previstas: releases de produção (operacional) e CVM (financeiro).
Dados de demonstração até a coleta real ser ligada.
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

import pandas as pd
import streamlit as st

from src.app_auth import exigir_login
from src.formato import fmt_moeda_mil
from src.persistence.db import fetch_df, init_schema
from src.services.setor import soma_metric, tendencia, variacao_pct
from src.theme import apply_theme

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Empresas", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

PERIODO_ATUAL = "3T26"
PERIODO_ANT = "3T25"

st.markdown('<div class="eyebrow">05 · Empresas — Usinas de capital aberto</div>', unsafe_allow_html=True)
st.title("Visão das empresas")

dados = fetch_df(
    """SELECT m.company_code, c.nome, c.ticker, m.metric, m.valor, m.unidade,
              m.periodo, m.safra, m.collector_version, m.data_publicacao, m.fonte
       FROM company_metrics m JOIN companies c ON c.code=m.company_code
       WHERE m.grupo='operacional'"""
)

if dados.empty:
    st.info("Sem dados de empresas ainda. Rode `python db/seeds/seed_demo.py`.")
    st.stop()

is_demo = (dados["collector_version"] == "demo").any()
if is_demo:
    st.markdown(
        '<div class="demobar">⬡ Dados de demonstração. Coleta real (releases + CVM) entra na sequência.</div>',
        unsafe_allow_html=True,
    )

# registros no formato que o serviço de setor espera
registros = [
    {"company": r["company_code"], "metric": r["metric"], "valor": r["valor"], "periodo": r["periodo"]}
    for _, r in dados.iterrows()
]

# ── leitura agregada do setor ────────────────────────────────────────────
st.markdown("##### Leitura do setor (usinas acompanhadas)")
moa_atual = soma_metric(registros, "moagem", PERIODO_ATUAL)
moa_ant = soma_metric(registros, "moagem", PERIODO_ANT)
var_moa = variacao_pct(moa_atual, moa_ant)
tend = tendencia(var_moa)
tend_cor = {"em alta": "up", "em queda": "down", "estável": "", "sem referência": ""}[tend]

ac_atual = soma_metric(registros, "prod_acucar", PERIODO_ATUAL)
et_atual = soma_metric(registros, "prod_etanol", PERIODO_ATUAL)

s1, s2, s3 = st.columns(3)
s1.markdown(
    f'<div class="cv-kpi"><div class="nm">Moagem do conjunto · {PERIODO_ATUAL}</div>'
    f'<div class="val">{moa_atual:.1f}<span style="font-size:13px"> Mt</span></div>'
    f'<div style="margin-top:6px"><span class="chip {tend_cor}">'
    f'{"+" if (var_moa or 0) >= 0 else ""}{var_moa}% vs {PERIODO_ANT} · {tend}</span></div></div>',
    unsafe_allow_html=True,
)
s2.markdown(
    f'<div class="cv-kpi"><div class="nm">Produção de açúcar · {PERIODO_ATUAL}</div>'
    f'<div class="val">{ac_atual:.0f}<span style="font-size:13px"> kt</span></div>'
    f'<div style="margin-top:6px"><span class="src">soma das usinas</span></div></div>',
    unsafe_allow_html=True,
)
s3.markdown(
    f'<div class="cv-kpi"><div class="nm">Produção de etanol · {PERIODO_ATUAL}</div>'
    f'<div class="val">{et_atual:.0f}<span style="font-size:13px"> mil m³</span></div>'
    f'<div style="margin-top:6px"><span class="src">soma das usinas</span></div></div>',
    unsafe_allow_html=True,
)

# ── cards por empresa ────────────────────────────────────────────────────
st.markdown("##### Resumo por usina")


def metrica(company: str, metric: str, periodo: str = PERIODO_ATUAL):
    sub = dados[(dados["company_code"] == company) & (dados["metric"] == metric) & (dados["periodo"] == periodo)]
    return sub.iloc[0]["valor"] if not sub.empty else None


empresas = dados[["company_code", "nome", "ticker"]].drop_duplicates()
empresas = empresas[empresas["company_code"].isin(
    dados[dados["periodo"] == PERIODO_ATUAL]["company_code"].unique()
)]

cols = st.columns(len(empresas)) if len(empresas) <= 3 else st.columns(3)
for i, (_, emp) in enumerate(empresas.iterrows()):
    co = emp["company_code"]
    moa = metrica(co, "moagem")
    moa_a = metrica(co, "moagem", PERIODO_ANT)
    vm = variacao_pct(moa, moa_a) if (moa and moa_a) else None
    mix_a = metrica(co, "mix_acucar")
    mix_e = metrica(co, "mix_etanol")
    atr = metrica(co, "atr")
    pac = metrica(co, "prod_acucar")
    pet = metrica(co, "prod_etanol")
    vm_cor = "up" if (vm or 0) >= 0 else "down"
    mix_bar = ""
    if mix_a and mix_e:
        mix_bar = (
            f'<div style="display:flex;height:8px;border-radius:4px;overflow:hidden;margin:8px 0">'
            f'<div style="width:{mix_a}%;background:#C6881C"></div>'
            f'<div style="width:{mix_e}%;background:#1F7A4D"></div></div>'
            f'<div class="src">açúcar {mix_a:.0f}% · etanol {mix_e:.0f}%</div>'
        )
    col = cols[i % 3]
    col.markdown(
        f'<div class="cv-card" style="padding:16px">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
        f'<b style="font-size:16px">{emp["nome"]}</b>'
        f'<span class="src mono">{emp["ticker"]}</span></div>'
        f'<div style="margin-top:10px"><span class="src">Moagem {PERIODO_ATUAL}</span><br>'
        f'<span class="mono" style="font-size:22px;font-weight:600">{moa:.1f} Mt</span> '
        f'<span class="chip {vm_cor}" style="font-size:11px">{"+" if (vm or 0)>=0 else ""}{vm}%</span></div>'
        f'{mix_bar}'
        f'<div style="display:flex;gap:18px;margin-top:10px">'
        f'<div><span class="src">ATR</span><br><span class="mono">{atr:.1f} kg/t</span></div>'
        f'<div><span class="src">Açúcar</span><br><span class="mono">{pac:.0f} kt</span></div>'
        f'<div><span class="src">Etanol</span><br><span class="mono">{pet:.0f} mil m³</span></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

# ── comparação lado a lado ───────────────────────────────────────────────
st.markdown("##### Comparação")
LABELS = {
    "moagem": "Moagem (Mt)", "mix_acucar": "Mix açúcar (%)", "mix_etanol": "Mix etanol (%)",
    "atr": "ATR (kg/t)", "prod_acucar": "Açúcar (kt)", "prod_etanol": "Etanol (mil m³)",
}
tabela = []
for metric, label in LABELS.items():
    linha = {"Indicador": label}
    for _, emp in empresas.iterrows():
        v = metrica(emp["company_code"], metric)
        linha[emp["nome"]] = v
    tabela.append(linha)
df_comp = pd.DataFrame(tabela).set_index("Indicador")
st.dataframe(df_comp, width="stretch")

# ── seção financeira (CVM) ───────────────────────────────────────────────
fin = fetch_df(
    """SELECT c.nome, m.metric, m.valor, m.status_validacao, m.data_referencia
       FROM company_metrics m JOIN companies c ON c.code=m.company_code
       WHERE m.grupo='financeiro' AND m.fonte LIKE 'cvm%'"""
)
if not fin.empty:
    st.markdown("### Financeiro")
    if (fin["status_validacao"] == "a_conferir").any():
        st.markdown(
            '<div class="demobar">⬡ Extraído automaticamente das demonstrações da CVM — '
            "confira na fonte oficial antes de usar em decisão.</div>",
            unsafe_allow_html=True,
        )

    FIN_LABELS = {
        "receita": "Receita líquida",
        "lucro_liquido": "Lucro líquido",
        "divida_total": "Dívida total",
    }
    empresas_fin = sorted(fin["nome"].drop_duplicates().tolist())
    cols_fin = st.columns(len(empresas_fin))
    for col, nome in zip(cols_fin, empresas_fin, strict=False):
        sub = fin[fin["nome"] == nome]
        ref = sub["data_referencia"].iloc[0] if not sub.empty else None
        ref_txt = ""
        if ref is not None and str(ref) != "None":
            try:
                ref_txt = date.fromisoformat(str(ref)[:10]).strftime("%d/%m/%Y")
            except ValueError:
                ref_txt = str(ref)
        linhas_html = []
        for metric, label in FIN_LABELS.items():
            v = sub[sub["metric"] == metric]["valor"]
            valor = float(v.iloc[0]) if not v.empty else None
            cor = "#B4462E" if (valor is not None and valor < 0) else "var(--tinta)"
            linhas_html.append(
                f'<div style="display:flex;justify-content:space-between;gap:10px;'
                f'padding:7px 0;border-bottom:1px solid rgba(20,87,58,.08)">'
                f'<span class="src" style="text-transform:none">{label}</span>'
                f'<span class="mono" style="font-weight:600;color:{cor}">'
                f"{fmt_moeda_mil(valor)}</span></div>"
            )
        with col:
            st.markdown(
                f'<div class="cv-card"><div style="font-weight:700;margin-bottom:6px">{nome}</div>'
                f'<div class="src" style="margin-bottom:8px">exercício {ref_txt}</div>'
                + "".join(linhas_html)
                + "</div>",
                unsafe_allow_html=True,
            )

st.markdown(
    '<div class="src" style="margin-top:14px;line-height:1.6">Dados operacionais divulgados pelas '
    "próprias usinas em releases de produção. A leitura agregada soma as usinas acompanhadas para "
    "indicar se a moagem do conjunto sobe ou desce. Período de referência: "
    f"{PERIODO_ATUAL}. Financeiro: CVM (demonstrações padronizadas).</div>",
    unsafe_allow_html=True,
)
