"""Página — Raio X: painel de carteira de crédito (só visualização).

Protegida pelo login individual: só quem está logado e aprovado vê. A carteira
é enviada por upload e vive só na sessão — NUNCA é salva. O único dado que
persiste é o comentário por cliente (ligado ao ID), guardado no banco.

Esta é a primeira fase da integração: upload + Resumo Executivo + Dashboard +
comentários. As demais abas vêm nas próximas fases.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_r = _os.path.abspath(_os.path.dirname(__file__))
while _r != "/" and not _os.path.isdir(_os.path.join(_r, "src")):
    _r = _os.path.dirname(_r)
if _r not in _sys.path:
    _sys.path.insert(0, _r)


import plotly.express as px
import streamlit as st

from src.app_auth import exigir_login
from src.contas import usuario_logado
from src.depara import (
    aplicar_depara,
    carregar_depara,
    importar_depara_excel,
    salvar_linha_depara,
)
from src.persistence.db import init_schema
from src.raiox import (
    BUCKET_ORDER,
    aplicar_comentarios,
    calcular_pd_e_rating_medio,
    ler_carteira_excel,
    normalize_base,
    salvar_comentario,
)
from src.theme import apply_theme

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Raio X", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

# ── porteiro: só quem tem login individual aprovado ──────────────────────
u = usuario_logado()
if not u:
    st.markdown('<div class="eyebrow">Raio X — carteira de crédito</div>', unsafe_allow_html=True)
    st.title("Raio X")
    st.info("Esta área exige **login individual**. Entre com sua conta em **Minha conta** "
            "para acessar o Raio X.")
    st.stop()


def _fmt_mm(x) -> str:
    """Formata em milhões de reais, padrão brasileiro."""
    try:
        return f"R$ {float(x):,.1f} mm".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "-"


st.markdown('<div class="eyebrow">Raio X — carteira de crédito · só visualização</div>',
            unsafe_allow_html=True)
st.title("Raio X")
st.caption("A carteira enviada vive só nesta sessão e não é salva. "
           "Apenas os comentários (por cliente) ficam guardados.")

# ── upload da carteira (na sessão) ───────────────────────────────────────
from src.raiox import (
    carregar_base_teste,
    excluir_base_teste,
    existe_base_teste,
    salvar_base_teste,
)

tem_base_salva = existe_base_teste()

with st.sidebar:
    st.markdown("### Carregar carteira")
    arquivo = st.file_uploader("Planilha da carteira (.xlsx)", type=["xlsx"])
    st.caption("O arquivo é processado na memória e descartado ao sair.")

    if tem_base_salva:
        st.markdown("---")
        if st.button("📂 Usar base de teste salva"):
            st.session_state["_raiox_fonte"] = "salva"
            st.rerun()

    st.markdown("---")
    # TEMPORÁRIO (testes): carteira fictícia embutida.
    usar_exemplo = st.button("🧪 Carregar carteira de exemplo")
    st.caption("Dados fictícios, só para testar. Remover depois.")

if usar_exemplo:
    st.session_state["_raiox_fonte"] = "exemplo"
if arquivo is not None:
    st.session_state["_raiox_fonte"] = "upload"

fonte = st.session_state.get("_raiox_fonte")

# lê e normaliza (na memória)
try:
    if fonte == "exemplo":
        from src.raiox_exemplo import carteira_exemplo
        base = normalize_base(carteira_exemplo())
    elif fonte == "salva" and tem_base_salva:
        base = carregar_base_teste()   # já vem normalizada
    elif arquivo is not None:
        base = normalize_base(ler_carteira_excel(arquivo))
    else:
        st.info("⬅️ Carregue a planilha da carteira, ou use a **carteira de exemplo** "
                "na barra lateral para testar.")
        st.stop()
    base = aplicar_depara(base)          # aplica o de-para salvo (analista/setor/ativo)
    base = aplicar_comentarios(base)
except Exception as exc:  # noqa: BLE001
    st.error(f"Não consegui ler a planilha: {exc}")
    st.stop()

# ── salvar / excluir base de teste (com aviso de segurança) ──────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("### Base de teste")
    if st.button("💾 Salvar base atual como teste"):
        salvar_base_teste(base, u["email"])
        st.success("Base de teste salva.")
        st.rerun()
    if tem_base_salva and st.button("🗑️ Excluir base de teste"):
        excluir_base_teste()
        st.session_state.pop("_raiox_fonte", None)
        st.success("Base de teste excluída.")
        st.rerun()

# aviso permanente de segurança quando há base salva na nuvem
if tem_base_salva or fonte == "salva":
    st.error("⚠️ **Base de teste salva na nuvem.** Use **apenas dados fictícios** "
             "aqui. Nunca salve carteira real. Exclua a base de teste ao terminar.")

if fonte == "exemplo":
    st.warning("🧪 Usando **carteira de exemplo** (dados fictícios, só para teste).")
st.success(f"Carteira carregada: **{len(base)}** clientes.")

# ── abas ─────────────────────────────────────────────────────────────────
abas = st.tabs([
    "Resumo Executivo", "Dashboard", "Comentários", "De-Para",
    "Tabelas de Rating", "Movimentações", "Próximos Vencimentos",
    "Visitas", "Clientes", "Qualidade", "Comparação M-1", "Exportar PDF",
])

# --- Resumo Executivo ---
with abas[0]:
    limite = base["limite"].sum()
    risco = base["risco"].sum()
    disp = base["disponibilidade"].sum()
    grupos = base["grupo"].nunique()
    pd_media, rating_medio = calcular_pd_e_rating_medio(base)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Limite total", _fmt_mm(limite))
    c2.metric("Risco total", _fmt_mm(risco))
    c3.metric("Disponibilidade", _fmt_mm(disp))
    c4.metric("Grupos", f"{grupos}")
    c5.metric("Rating médio", rating_medio)

    st.markdown("---")
    st.markdown("##### Risco por faixa de rating")
    if "bucket_rating" in base.columns:
        por_faixa = (
            base.groupby("bucket_rating")["risco"].sum()
            .reindex(BUCKET_ORDER).dropna().reset_index()
        )
        if not por_faixa.empty:
            fig = px.bar(por_faixa, x="bucket_rating", y="risco",
                         labels={"bucket_rating": "Faixa", "risco": "Risco (R$)"})
            st.plotly_chart(fig, width="stretch")

# --- Dashboard ---
with abas[1]:
    st.markdown("##### Risco por setor gerencial")
    por_setor = (
        base.groupby("setor_gerencial")["risco"].sum()
        .sort_values(ascending=False).head(15).reset_index()
    )
    if not por_setor.empty:
        fig = px.bar(por_setor, x="risco", y="setor_gerencial", orientation="h",
                     labels={"risco": "Risco (R$)", "setor_gerencial": "Setor"})
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")

    st.markdown("##### Maiores riscos (top 15 grupos)")
    top = base.groupby("grupo")["risco"].sum().sort_values(ascending=False).head(15)
    st.dataframe(top.reset_index().rename(columns={"grupo": "Grupo", "risco": "Risco"}),
                 width="stretch", hide_index=True)

# --- Comentários (o dado que persiste) ---
with abas[2]:
    st.markdown("##### Comentários por cliente")
    st.caption("O comentário fica salvo e reaparece quando você subir a carteira de novo. "
               "A carteira em si não é salva.")
    grupos_lista = base[["id", "grupo"]].drop_duplicates().sort_values("grupo")
    rotulos = {f'{r["grupo"]} (ID {r["id"]})': r["id"]
               for _, r in grupos_lista.iterrows()}
    escolha = st.selectbox("Cliente", list(rotulos.keys()))
    if escolha:
        cid = rotulos[escolha]
        atual = base[base["id"] == cid].iloc[0]
        novo_status = st.text_input("Status", value=str(atual.get("status", "") or ""))
        novo_com = st.text_area("Comentário",
                                value=str(atual.get("comentario", "") or ""), height=120)
        if st.button("Salvar comentário", type="primary"):
            salvar_comentario(cid, novo_status, novo_com, u["email"])
            st.success("Comentário salvo. Reaparece na próxima vez que subir a carteira.")

# --- De-Para (editável, salvo no banco) ---
with abas[3]:
    st.markdown("##### De-Para — analista, setor e ativo/inativo por cliente")
    st.caption("O de-para fica salvo (é só configuração, sem dado de crédito). "
               "É aplicado sobre a carteira: muda analista/setor e remove os inativos.")

    with st.expander("Importar de-para de uma planilha (.xlsx)"):
        arq_dep = st.file_uploader("Planilha de de-para", type=["xlsx"], key="dep_upload")
        if arq_dep is not None and st.button("Importar de-para"):
            n, msg = importar_depara_excel(arq_dep, u["email"])
            (st.success if n else st.error)(msg)
            if n:
                st.rerun()

    st.markdown("**Editar um cliente**")
    grupos_dep = base[["id", "grupo"]].drop_duplicates().sort_values("grupo")
    rot_dep = {f'{r["grupo"]} (ID {r["id"]})': r["id"] for _, r in grupos_dep.iterrows()}
    if rot_dep:
        esc = st.selectbox("Cliente", list(rot_dep.keys()), key="dep_cliente")
        cid = rot_dep[esc]
        linha = base[base["id"] == cid].iloc[0]
        col_a, col_b = st.columns(2)
        with col_a:
            novo_analista = st.text_input("Analista", value=str(linha.get("analista", "") or ""))
        with col_b:
            novo_setor = st.text_input("Setor gerencial",
                                       value=str(linha.get("setor_gerencial", "") or ""))
        ativo = st.checkbox("Cliente ativo", value=True)
        if st.button("Salvar de-para deste cliente", type="primary"):
            salvar_linha_depara(cid, novo_analista, novo_setor, 1 if ativo else 0,
                                u["email"], grupo=str(linha.get("grupo", "") or ""))
            st.success("De-para salvo. Aplicado quando a carteira for recarregada.")

    dep_salvo = carregar_depara()
    if not dep_salvo.empty:
        st.markdown(f"**De-para salvo · {len(dep_salvo)} clientes**")
        st.dataframe(dep_salvo, width="stretch", hide_index=True)

# --- abas ainda em construção ---
_em_construcao = {
    4: "Tabelas de Rating", 5: "Movimentações", 6: "Próximos Vencimentos",
    7: "Visitas", 8: "Clientes", 9: "Qualidade", 10: "Comparação M-1",
    11: "Exportar PDF",
}
for idx, nome in _em_construcao.items():
    with abas[idx]:
        st.info(f"A aba **{nome}** será adicionada na próxima fase da integração.")
