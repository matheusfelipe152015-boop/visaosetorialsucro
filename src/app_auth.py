"""Portão de acesso (login por senha única de equipe).

Protege todas as telas com uma senha compartilhada. A senha NÃO fica escrita no
código: é lida de st.secrets (cofre do Streamlit Cloud) ou da variável de
ambiente APP_PASSWORD. Enquanto nenhuma senha estiver configurada, o portão fica
aberto (útil em desenvolvimento local).

Uso em cada página, logo após import do streamlit:
    from app._auth import exigir_login
    exigir_login()
"""

from __future__ import annotations

import hmac
import os

import streamlit as st

# Ponte cofre -> ambiente: na nuvem do Streamlit, os segredos (DATABASE_URL,
# APP_PASSWORD) ficam em st.secrets. O restante do projeto lê de variáveis de
# ambiente. Copiamos um para o outro AQUI, que é importado no topo de cada
# página, antes de a configuração do banco ser carregada.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, str):
            os.environ.setdefault(_k, _v)
except Exception:
    pass


def _senha_configurada() -> str | None:
    """Lê a senha do cofre (st.secrets) ou do ambiente. None = sem senha definida."""
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"])
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD")


def exigir_login() -> None:
    """Bloqueia a página até a senha correta ser informada.

    Se nenhuma senha estiver configurada (dev local), libera o acesso.
    """
    senha_certa = _senha_configurada()
    if not senha_certa:
        return  # sem senha definida -> acesso liberado (ambiente local)

    if st.session_state.get("_autenticado"):
        return  # já entrou nesta sessão

    # tela de login
    st.markdown(
        """
        <div style="max-width:420px;margin:8vh auto 0;text-align:center">
          <div style="font-family:'Bricolage Grotesque',sans-serif;font-size:30px;
               font-weight:700;color:#14573A">VISÃO SETORIAL SUCRO</div>
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
    st.stop()  # impede o resto da página de carregar enquanto não logar
