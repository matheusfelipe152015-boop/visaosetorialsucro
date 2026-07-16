"""Pagina — Administracao: aprovar cadastros e gerir niveis de acesso.

So aparece para ADM e gerencia. Analista ou nao-logado ve apenas um aviso.
As acoes respeitam as regras: gerencia nao cria ADM; ninguem mexe em si mesmo.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_r = _os.path.abspath(_os.path.dirname(__file__))
while _r != "/" and not _os.path.isdir(_os.path.join(_r, "src")):
    _r = _os.path.dirname(_r)
if _r not in _sys.path:
    _sys.path.insert(0, _r)


import streamlit as st

from src.app_auth import exigir_login
from src.contas import (
    aprovar,
    listar_usuarios,
    mudar_papel,
    papeis_que_pode_conceder,
    pode_administrar,
    revogar,
    usuario_logado,
)
from src.persistence.db import init_schema
from src.theme import apply_theme

st.set_page_config(page_title="VISAO SETORIAL SUCRO . Administracao", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

_NIVEL_TXT = {"adm": "Administrador", "gerencia": "Gerencia", "analista": "Analista"}

u = usuario_logado()

if not u or not pode_administrar(u["papel"]):
    st.markdown('<div class="eyebrow">Administracao</div>', unsafe_allow_html=True)
    st.title("Administracao")
    st.info("Esta area e restrita a administradores e gerencia. "
            "Entre com uma conta autorizada em **Minha conta**.")
    st.stop()

st.markdown('<div class="eyebrow">Administracao — usuarios e acessos</div>', unsafe_allow_html=True)
st.title("Administracao")

concede = papeis_que_pode_conceder(u["papel"])
usuarios = listar_usuarios()
pendentes = usuarios[usuarios["situacao"] == "pendente"]
ativos = usuarios[usuarios["situacao"] == "ativo"]

st.markdown(f"##### Aguardando aprovacao . {len(pendentes)}")
if pendentes.empty:
    st.caption("Nenhum cadastro pendente.")
else:
    for _, r in pendentes.iterrows():
        with st.container():
            st.markdown(
                f'<div class="cv-card"><b>{r["nome"] or "(sem nome)"}</b> '
                f'<span class="src">. {r["email"]}</span></div>',
                unsafe_allow_html=True,
            )
            c1, c2, _x = st.columns([2, 1, 3])
            with c1:
                papel_sel = st.selectbox(
                    "Conceder nivel", concede, key=f"papel_{r['id']}",
                    format_func=lambda p: _NIVEL_TXT.get(p, p),
                )
            with c2:
                st.write("")
                st.write("")
                if st.button("Aprovar", key=f"aprovar_{r['id']}", type="primary"):
                    ok, msg = aprovar(r["id"], papel_sel, u)
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

st.markdown("---")

st.markdown(f"##### Usuarios ativos . {len(ativos)}")
if ativos.empty:
    st.caption("Nenhum usuario ativo ainda.")
else:
    for _, r in ativos.iterrows():
        sou_eu = r["id"] == u["id"]
        with st.container():
            st.markdown(
                f'<div class="cv-card"><b>{r["nome"] or "(sem nome)"}</b> '
                f'<span class="src">. {r["email"]} . '
                f'{_NIVEL_TXT.get(r["papel"], r["papel"])}'
                f'{" . (voce)" if sou_eu else ""}</span></div>',
                unsafe_allow_html=True,
            )
            if sou_eu:
                continue
            c1, c2, c3 = st.columns([2, 1, 3])
            with c1:
                if concede:
                    novo = st.selectbox(
                        "Alterar nivel", concede, key=f"novo_{r['id']}",
                        index=concede.index(r["papel"]) if r["papel"] in concede else 0,
                        format_func=lambda p: _NIVEL_TXT.get(p, p),
                    )
            with c2:
                st.write("")
                st.write("")
                if concede and st.button("Salvar", key=f"salvar_{r['id']}"):
                    ok, msg = mudar_papel(r["id"], novo, u)
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()
            with c3:
                st.write("")
                st.write("")
                if st.button("Revogar acesso", key=f"revogar_{r['id']}"):
                    ok, msg = revogar(r["id"], u)
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()
