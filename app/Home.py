"""Ponto de entrada com navegação controlada por login.

Regras de visibilidade do menu:
  · Sempre: as 8 telas públicas do setor + "Minha conta".
  · Só com login individual: "Anotações" e "Raio X".
  · Só para ADM/gerência: "Administração".

Isso esconde os ITENS do menu. A trava de segurança de verdade continua dentro
de cada página protegida (que bloqueia o conteúdo se não houver login). Aqui é a
camada visual: não mostrar portas que a pessoa não pode abrir.
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

st.set_page_config(page_title="VISÃO SETORIAL SUCRO", page_icon="⬡", layout="wide")

from src.contas import pode_administrar, usuario_logado

_AQUI = _os.path.dirname(__file__)


def _pg(arquivo: str, titulo: str, icone: str, default: bool = False):
    return st.Page(_os.path.join(_AQUI, arquivo), title=titulo, icon=icone, default=default)


# páginas públicas (sempre visíveis)
publicas = [
    _pg("pages/1_Visao_executiva.py", "Visão executiva", "🏠", default=True),
    _pg("pages/2_Indicadores.py", "Indicadores", "📊"),
    _pg("pages/3_Mercado.py", "Mercado", "📈"),
    _pg("pages/4_Precos.py", "Preços por estado", "🗺️"),
    _pg("pages/5_Empresas.py", "Empresas", "🏭"),
    _pg("pages/6_Clima.py", "Clima", "🌦️"),
    _pg("pages/7_Safra.py", "Safra", "🌱"),
    _pg("pages/8_Saude_dos_dados.py", "Saúde dos dados", "🩺"),
]

conta = [_pg("pages/10_Minha_conta.py", "Minha conta", "👤")]

# páginas que exigem login individual
u = usuario_logado()
restritas = []
if u:
    restritas = [
        _pg("pages/9_Anotacoes.py", "Anotações", "📝"),
        _pg("pages/12_Raio_X.py", "Raio X", "🔎"),
    ]

# administração: só adm/gerência
admin = []
if u and pode_administrar(u.get("papel", "")):
    admin = [_pg("pages/11_Administracao.py", "Administração", "⚙️")]

# monta o menu por seções
grupos = {"Plataforma": publicas, "Conta": conta}
if restritas:
    grupos["Restrito"] = restritas
if admin:
    grupos["Gestão"] = admin

pg = st.navigation(grupos)
pg.run()
