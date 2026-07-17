"""Página 9 — Anotações: registros escritos manualmente, salvos no banco.

Campo de título, campo de conteúdo, botão salvar, lista das anotações, com
editar e excluir. Persiste no banco (Supabase/SQLite), então continua salvo
ao atualizar, fechar e reabrir.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_r = _os.path.abspath(_os.path.dirname(__file__))
while _r != "/" and not _os.path.isdir(_os.path.join(_r, "src")):
    _r = _os.path.dirname(_r)
if _r not in _sys.path:
    _sys.path.insert(0, _r)


from datetime import datetime

import streamlit as st

from src.anotacoes import (
    atualizar_anotacao,
    criar_anotacao,
    excluir_anotacao,
    listar_anotacoes,
)
from src.app_auth import exigir_login
from src.persistence.db import init_schema
from src.theme import apply_theme

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Anotações", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()


def _fmt_data(v) -> str:
    """Formata a data/hora de atualização para exibição."""
    if v is None or str(v) == "None":
        return ""
    try:
        dt = datetime.fromisoformat(str(v)[:19])
        return dt.strftime("%d/%m/%Y às %H:%M")
    except ValueError:
        return str(v)[:16]


st.markdown('<div class="eyebrow">09 · Anotações — registros do setor</div>', unsafe_allow_html=True)
st.title("Anotações")

# ── formulário de nova anotação (ou edição) ──────────────────────────────
# guardamos em session_state qual anotação está sendo editada (se houver)
editando = st.session_state.get("anot_editando")

if editando:
    st.markdown(
        '<div class="src" style="margin-bottom:6px">Editando anotação</div>',
        unsafe_allow_html=True,
    )

titulo = st.text_input(
    "Título",
    value=editando["titulo"] if editando else "",
    key="anot_titulo",
    placeholder="Ex.: Reunião com usina X, insight sobre paridade...",
)
conteudo = st.text_area(
    "Conteúdo",
    value=editando["conteudo"] if editando else "",
    key="anot_conteudo",
    height=180,
    placeholder="Escreva aqui sua anotação...",
)

col_salvar, col_cancelar, _ = st.columns([1, 1, 4])
with col_salvar:
    if st.button("Salvar", type="primary", width="stretch"):
        if not titulo.strip() and not conteudo.strip():
            st.warning("Escreva ao menos um título ou conteúdo.")
        else:
            titulo_final = titulo.strip() or "(sem título)"
            if editando:
                atualizar_anotacao(editando["id"], titulo_final, conteudo)
                st.session_state.pop("anot_editando", None)
                st.success("Anotação atualizada.")
            else:
                criar_anotacao(titulo_final, conteudo)
                st.success("Anotação salva.")
            # limpa os campos e recarrega
            st.session_state.pop("anot_titulo", None)
            st.session_state.pop("anot_conteudo", None)
            st.rerun()

if editando:
    with col_cancelar:
        if st.button("Cancelar", width="stretch"):
            st.session_state.pop("anot_editando", None)
            st.session_state.pop("anot_titulo", None)
            st.session_state.pop("anot_conteudo", None)
            st.rerun()

st.markdown("---")

# ── lista das anotações salvas ───────────────────────────────────────────
anotacoes = listar_anotacoes()

if anotacoes.empty:
    st.markdown(
        '<div class="src" style="padding:20px 0">Nenhuma anotação ainda. '
        "Escreva a primeira acima.</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(f"##### Salvas · {len(anotacoes)}")
    for _, r in anotacoes.iterrows():
        with st.container():
            st.markdown(
                f'<div class="cv-card" style="margin-bottom:2px">'
                f'<div style="font-weight:700;font-size:16px">{r["titulo"]}</div>'
                f'<div class="src" style="margin:4px 0 10px">atualizada em {_fmt_data(r["atualizada_em"])}</div>'
                f'<div style="white-space:pre-wrap;line-height:1.55">{r["conteudo"]}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
            c_edit, c_del, _ = st.columns([1, 1, 6])
            with c_edit:
                if st.button("Editar", key=f"edit_{r['id']}", width="stretch"):
                    st.session_state["anot_editando"] = {
                        "id": r["id"], "titulo": r["titulo"], "conteudo": r["conteudo"],
                    }
                    st.session_state.pop("anot_titulo", None)
                    st.session_state.pop("anot_conteudo", None)
                    st.rerun()
            with c_del:
                if st.button("Excluir", key=f"del_{r['id']}", width="stretch"):
                    # confirmação em duas etapas para não apagar sem querer
                    if st.session_state.get("anot_confirma_del") == r["id"]:
                        excluir_anotacao(r["id"])
                        st.session_state.pop("anot_confirma_del", None)
                        st.rerun()
                    else:
                        st.session_state["anot_confirma_del"] = r["id"]
                        st.rerun()
            if st.session_state.get("anot_confirma_del") == r["id"]:
                st.warning("Clique em **Excluir** de novo para confirmar a exclusão.")
