"""Acesso ao banco. SQLite local por padrão; PostgreSQL/Supabase via DATABASE_URL."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, text

from config.settings import settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"

_BENIGN = ("already exists", "duplicate column")

# Otimização: o schema só precisa ser conferido uma vez por processo.
_schema_ready = False


@lru_cache(maxsize=2)
def get_engine(readonly: bool = False) -> Engine:
    url = settings.sqlalchemy_url_ro if readonly else settings.sqlalchemy_url
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {"prepare_threshold": None}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)


def init_schema() -> None:
    """Aplica as migrações uma vez por processo. Reexecução é barata (no-op)."""
    global _schema_ready
    if _schema_ready:
        return
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
                    continue
                raise
    _schema_ready = True


def _fetch_df_raw(query: str, params: dict | None = None):
    import pandas as pd

    with get_engine(readonly=True).connect() as conn:
        return pd.read_sql_query(text(query), conn, params=params or {})


# Sob o Streamlit, cacheia consultas por 5 min. Fora dele (robô/testes), sem cache.
try:
    import streamlit as st

    @st.cache_data(ttl=600, show_spinner=False)
    def _fetch_df_cached(query: str, params: dict | None = None):
        return _fetch_df_raw(query, params)

    def fetch_df(query: str, params: dict | None = None):
        return _fetch_df_cached(query, params)

except Exception:
    def fetch_df(query: str, params: dict | None = None):
        return _fetch_df_raw(query, params)
