"""Anotacoes do usuario — salvar, listar, editar e excluir.

Guarda no mesmo banco da plataforma (Supabase na nuvem, SQLite local), entao as
anotacoes persistem entre sessoes e ate entre dispositivos.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from src.persistence.db import _fetch_df_raw, get_engine


def criar_anotacao(titulo, conteudo):
    """Cria uma anotacao nova e devolve o id."""
    aid = uuid.uuid4().hex
    agora = datetime.utcnow()
    with get_engine().begin() as conn:
        conn.execute(
            text("""INSERT INTO anotacoes(id, titulo, conteudo, criada_em, atualizada_em)
                    VALUES(:id, :t, :c, :ca, :at)"""),
            {"id": aid, "t": titulo.strip(), "c": conteudo.strip(),
             "ca": agora, "at": agora},
        )
    return aid


def atualizar_anotacao(aid, titulo, conteudo):
    """Atualiza titulo e conteudo de uma anotacao existente."""
    with get_engine().begin() as conn:
        conn.execute(
            text("""UPDATE anotacoes
                    SET titulo = :t, conteudo = :c, atualizada_em = :at
                    WHERE id = :id"""),
            {"id": aid, "t": titulo.strip(), "c": conteudo.strip(),
             "at": datetime.utcnow()},
        )


def excluir_anotacao(aid):
    """Remove uma anotacao."""
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM anotacoes WHERE id = :id"), {"id": aid})


def listar_anotacoes():
    """Lista as anotacoes, mais recentes primeiro (sem cache: muda na hora)."""
    return _fetch_df_raw(
        "SELECT id, titulo, conteudo, criada_em, atualizada_em "
        "FROM anotacoes ORDER BY atualizada_em DESC"
    )
