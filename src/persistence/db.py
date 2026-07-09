"""Acesso ao banco. SQLite local por padrão; PostgreSQL/Supabase via DATABASE_URL."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, text

from config.settings import settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"

# Trechos de erro considerados benignos ao reaplicar uma migração (idempotência).
_BENIGN = ("already exists", "duplicate column")


@lru_cache(maxsize=2)
def get_engine(readonly: bool = False) -> Engine:
    url = settings.sqlalchemy_url_ro if readonly else settings.sqlalchemy_url
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        # Pooler do Supabase (porta 6543) nao aceita prepared statements.
        # prepare_threshold=None desliga isso de vez no psycopg.
        connect_args = {"prepare_threshold": None}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)


def init_schema() -> None:
    """Aplica todas as migrações em ordem. Reexecução é segura.

    Cada comando roda em sua própria transação. Isso é essencial no PostgreSQL:
    um erro benigno (ex.: coluna já existe) não contamina os comandos seguintes,
    pois no Postgres um erro aborta o bloco inteiro da transação.
    """
    eng = get_engine()
    is_sqlite = eng.url.get_backend_name() == "sqlite"
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        for stmt in (s.strip() for s in sql.split(";")):
            if not stmt:
                continue
            try:
                with eng.begin() as conn:
                    if is_sqlite:
                        conn.exec_driver_sql("PRAGMA foreign_keys=ON;")
                    conn.exec_driver_sql(stmt)
            except Exception as exc:  # noqa: BLE001
                if any(b in str(exc).lower() for b in _BENIGN):
                    continue  # coluna/tabela já existe — ok ao reaplicar
                raise


def fetch_df(query: str, params: dict | None = None):
    import pandas as pd

    with get_engine(readonly=True).connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params or {})
