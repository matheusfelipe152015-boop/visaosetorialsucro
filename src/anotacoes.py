"""Anotações do usuário — salvar, listar, editar e excluir.

Guarda no mesmo banco da plataforma (Supabase na nuvem, SQLite local), então as
anotações persistem entre sessões e até entre dispositivos. Nada de localStorage
— aqui o banco faz esse papel, e melhor.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from src.persistence.db import _fetch_df_raw, get_engine


def criar_anotacao(titulo: str, conteudo: str) -> str:
    """Cria uma anotação nova e devolve o id."""
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


def atualizar_anotacao(aid: str, titulo: str, conteudo: str) -> None:
    """Atualiza título e conteúdo de uma anotação existente."""
    with get_engine().begin() as conn:
        conn.execute(
            text("""UPDATE anotacoes
                    SET titulo = :t, conteudo = :c, atualizada_em = :at
                    WHERE id = :id"""),
            {"id": aid, "t": titulo.strip(), "c": conteudo.strip(),
             "at": datetime.utcnow()},
        )


def excluir_anotacao(aid: str) -> None:
    """Remove uma anotação."""
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM anotacoes WHERE id = :id"), {"id": aid})


def listar_anotacoes() -> pd.DataFrame:
    """Lista as anotações, mais recentes primeiro.

    Usa a leitura sem cache: como as anotações mudam por ação direta do usuário
    (salvar/excluir), o resultado precisa refletir na hora.
    """
    return _fetch_df_raw(
        "SELECT id, titulo, conteudo, criada_em, atualizada_em "
        "FROM anotacoes ORDER BY atualizada_em DESC"
    )
