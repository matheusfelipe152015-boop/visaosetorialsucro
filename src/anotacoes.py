"""Anotações do usuário — salvar, listar, editar e excluir.

Guarda no mesmo banco da plataforma (Supabase na nuvem, SQLite local), então as
anotações persistem entre sessões e dispositivos. Uma anotação pode ter uma
imagem (print) anexada, guardada como texto base64 no próprio banco.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from src.persistence.db import _fetch_df_raw, get_engine


def criar_anotacao(titulo: str, conteudo: str, imagem: str | None = None) -> str:
    """Cria uma anotação nova (com imagem opcional) e devolve o id."""
    aid = uuid.uuid4().hex
    agora = datetime.utcnow()
    with get_engine().begin() as conn:
        conn.execute(
            text("""INSERT INTO anotacoes(id, titulo, conteudo, imagem, criada_em, atualizada_em)
                    VALUES(:id, :t, :c, :img, :ca, :at)"""),
            {"id": aid, "t": titulo.strip(), "c": conteudo.strip(),
             "img": imagem, "ca": agora, "at": agora},
        )
    return aid


def atualizar_anotacao(aid: str, titulo: str, conteudo: str,
                       imagem: str | None = None) -> None:
    """Atualiza uma anotação. Se imagem for None, mantém a que já existe."""
    with get_engine().begin() as conn:
        if imagem is None:
            conn.execute(
                text("""UPDATE anotacoes
                        SET titulo = :t, conteudo = :c, atualizada_em = :at
                        WHERE id = :id"""),
                {"id": aid, "t": titulo.strip(), "c": conteudo.strip(),
                 "at": datetime.utcnow()},
            )
        else:
            conn.execute(
                text("""UPDATE anotacoes
                        SET titulo = :t, conteudo = :c, imagem = :img, atualizada_em = :at
                        WHERE id = :id"""),
                {"id": aid, "t": titulo.strip(), "c": conteudo.strip(),
                 "img": imagem, "at": datetime.utcnow()},
            )


def remover_imagem(aid: str) -> None:
    """Remove só a imagem de uma anotação (mantém o texto)."""
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE anotacoes SET imagem = NULL WHERE id = :id"), {"id": aid}
        )


def excluir_anotacao(aid: str) -> None:
    """Remove uma anotação."""
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM anotacoes WHERE id = :id"), {"id": aid})


def listar_anotacoes() -> pd.DataFrame:
    """Lista as anotações, mais recentes primeiro (sem cache: muda na hora)."""
    return _fetch_df_raw(
        "SELECT id, titulo, conteudo, imagem, criada_em, atualizada_em "
        "FROM anotacoes ORDER BY atualizada_em DESC"
    )
