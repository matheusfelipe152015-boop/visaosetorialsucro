"""Portão de acesso (login por senha única de equipe)."""

from __future__ import annotations

import hmac
import os

import streamlit as st

# Ponte cofre -> ambiente: na nuvem do Streamlit, os segredos ficam em
# st.secrets. O resto do projeto lê de variáveis de ambiente. Copiamos aqui.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass


def _senha_configurada() -> str | None:
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"])
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD")


def exigir_login() -> None:
    senha_certa = _senha_configurada()
    if not senha_certa:
        return
    if st.session_state.get("_autenticado"):
        return
    st.markdown(
        """
        <div style="max-width:420px;margin:8vh auto 0;text-align:center">
          <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:30px;
               font-weight:700;color:#14573A">CANAVIS</div>
          <div style="color:#5C6B63;margin:6px 0 26px">Inteligência do setor sucroenergético</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col = st.columns([1, 2, 1])[1]
    with col:
        senha = st.text_input("Senha de acesso", type="password", key="_senha_input")
        if st.button("Entrar", width="stretch"):
            if hmac.compare_digest(senha, senha_certa):
                st.session_state["_autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta. Tente novamente.")
    st.stop()
