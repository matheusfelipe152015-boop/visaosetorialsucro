"""Garante que reexecutar a coleta não cria registros duplicados (idempotência)."""

import importlib
from datetime import date, datetime

from sqlalchemy import text


def _fresh_db(tmp_path, monkeypatch):
    """Aponta o app para um SQLite temporário e recarrega os módulos de banco."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    import config.settings as cfg
    importlib.reload(cfg)
    import src.persistence.db as db
    importlib.reload(db)
    import src.persistence.repositories as repo
    importlib.reload(repo)

    db.init_schema()
    with db.get_engine().begin() as c:
        c.execute(text("INSERT INTO sources(code,nome) VALUES('bcb_sgs','BCB')"))
        c.execute(text("INSERT INTO indicators(code,nome) VALUES('usd_brl','USD/BRL')"))
    return db, repo


def test_upsert_idempotent(tmp_path, monkeypatch):
    db, repo = _fresh_db(tmp_path, monkeypatch)
    from src.domain.models import IndicatorValue

    vals = [
        IndicatorValue(
            indicator_code="usd_brl", source_code="bcb_sgs",
            data_referencia=date(2026, 6, 20), valor=5.4127, unidade="BRL/USD",
            data_coleta=datetime.utcnow(),
        )
    ]

    new1 = repo.upsert_indicator_values(vals)
    new2 = repo.upsert_indicator_values(vals)  # mesma coleta de novo

    assert new1 == 1
    assert new2 == 0
    count = db.fetch_df("SELECT COUNT(*) c FROM indicator_values").iloc[0]["c"]
    assert count == 1
