"""Verifica o catálogo semeado: contagem, destaques e itens planejados."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _seed_into(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'cat.db'}")
    import config.settings as cfg
    importlib.reload(cfg)
    import src.persistence.db as db
    importlib.reload(db)
    import src.persistence.repositories as repo
    importlib.reload(repo)
    # carrega o seed do arquivo (db/seeds não é pacote) e executa
    spec = importlib.util.spec_from_file_location("seed_demo", ROOT / "db" / "seeds" / "seed_demo.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    seed.run()
    return db


def test_catalogo_semeado(tmp_path, monkeypatch):
    db = _seed_into(tmp_path, monkeypatch)
    inds = db.fetch_df("SELECT code, destaque FROM indicators")
    assert len(inds) >= 18  # catálogo amplo
    assert int((inds["destaque"] == 1).sum()) == 5  # KPIs do painel

    cov = db.fetch_df(
        """SELECT i.code, COUNT(v.id) n FROM indicators i
           LEFT JOIN indicator_values v ON v.indicator_code=i.code GROUP BY i.code"""
    )
    assert int((cov["n"] == 0).sum()) >= 8   # ainda há vários planejados (sem coleta)
    assert int((cov["n"] > 0).sum()) == 10    # 5 destaques + 3 ANP + 2 exportações Comex


def test_seed_idempotente_catalogo(tmp_path, monkeypatch):
    db = _seed_into(tmp_path, monkeypatch)
    before = db.fetch_df("SELECT COUNT(*) c FROM indicator_values").iloc[0]["c"]
    # roda o seed de novo no mesmo banco
    spec = importlib.util.spec_from_file_location("seed_demo2", ROOT / "db" / "seeds" / "seed_demo.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    seed.run()
    after = db.fetch_df("SELECT COUNT(*) c FROM indicator_values").iloc[0]["c"]
    assert before == after  # nada duplicado
