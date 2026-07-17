"""Página — Minha conta: entrar, cadastrar e ver o nível de acesso.

A senha única continua abrindo a plataforma. Este login individual é um
segundo portão, mais forte, que dá acesso ao Raio X (a integrar depois).
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
from src.contas import autenticar, cadastrar, usuario_logado
from src.persistence.db import init_schema
from src.theme import apply_theme

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Minha conta", page_icon="⬡", layout="wide")
exigir_login()          # senha única da plataforma
init_schema()
apply_theme()

_NIVEL_TXT = {
    "adm": "Administrador",
    "gerencia": "Gerência",
    "analista": "Analista",
}

st.markdown('<div class="eyebrow">Minha conta — acesso individual</div>', unsafe_allow_html=True)
st.title("Minha conta")

u = usuario_logado()

# ── já logado: mostra quem é e oferece sair ──────────────────────────────
if u:
    st.success(f"Você está conectado como **{u['nome'] or u['email']}**.")
    st.markdown(
        f'<div class="cv-card"><div class="src">Nível de acesso</div>'
        f'<div style="font-size:20px;font-weight:700;margin-top:4px">'
        f'{_NIVEL_TXT.get(u["papel"], u["papel"])}</div></div>',
        unsafe_allow_html=True,
    )
    st.write("")
    if u["papel"] in ("adm", "gerencia"):
        st.info("Você tem acesso à tela de **Administração** (no menu ao lado).")
    if st.button("Sair da conta"):
        st.session_state.pop("_usuario", None)
        st.rerun()
    st.stop()

# ── não logado: abas Entrar / Cadastrar ──────────────────────────────────
aba_entrar, aba_cadastrar = st.tabs(["Entrar", "Criar cadastro"])

with aba_entrar:
    st.markdown("##### Entrar com email e senha")
    email = st.text_input("Email", key="login_email")
    senha = st.text_input("Senha", type="password", key="login_senha")
    if st.button("Entrar", type="primary"):
        usuario, msg = autenticar(email, senha)
        if usuario:
            st.session_state["_usuario"] = usuario
            st.rerun()
        else:
            st.error(msg)

with aba_cadastrar:
    st.markdown("##### Criar um novo cadastro")
    st.caption(
        "Após o cadastro, seu acesso fica pendente até um administrador ou "
        "gerente aprovar."
    )
    nome_c = st.text_input("Nome", key="cad_nome")
    email_c = st.text_input("Email", key="cad_email")
    senha_c = st.text_input(
        "Senha (mínimo 8 caracteres, com letras e números)",
        type="password", key="cad_senha",
    )
    senha_c2 = st.text_input("Repita a senha", type="password", key="cad_senha2")
    if st.button("Criar cadastro"):
        if senha_c != senha_c2:
            st.error("As senhas não conferem.")
        else:
            ok, msg = cadastrar(email_c, nome_c, senha_c)
            if ok:
                st.success(msg)
            else:
                st.error(msg)
