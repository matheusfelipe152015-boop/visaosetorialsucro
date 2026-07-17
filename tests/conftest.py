"""Configuração compartilhada dos testes.

Garante que o schema exista e que as tabelas que os testes gravam comecem
limpas (senão um teste "suja" o outro).
"""

import pytest


@pytest.fixture(autouse=True)
def _schema():
    """Cria as tabelas e limpa as que os testes escrevem, antes de cada teste."""
    import importlib

    from sqlalchemy import text

    import config.settings as _cfg
    importlib.reload(_cfg)
    from src.persistence import db as _db
    importlib.reload(_db)
    _db.get_engine.cache_clear()
    _db._schema_ready = False
    _db.init_schema()
    get_engine = _db.get_engine
    # limpa o cache do Streamlit (senão leituras antigas vazam entre testes)
    try:
        import streamlit as st
        st.cache_data.clear()
    except Exception:  # noqa: BLE001, S110
        pass
    # limpa tabelas de escrita para isolar os testes
    with get_engine().begin() as conn:
        for tabela in ("raiox_comentarios", "depara", "anotacoes", "usuarios"):
            try:
                conn.execute(text(f"DELETE FROM {tabela}"))
            except Exception:  # noqa: BLE001, S110 — tabela pode não existir ainda
                pass
    yield
