"""Testa os coletores de mercado (CFTC, curva, basis, finviz, ENSO)."""

import src.collectors.market.mercado_intel as m


def _prep(monkeypatch, conteudo):
    monkeypatch.setattr(m, "_baixar", lambda arquivo: conteudo)


def test_cftc(monkeypatch, tmp_path):
    import os

    from sqlalchemy import text

    from src.persistence.db import get_engine, init_schema
    os.environ["DATABASE_URL"] = ""
    init_schema()
    sql = open("db/migrations/0015_mercado_series.sql").read()
    with get_engine().begin() as c:
        for cmd in sql.split(";"):
            if cmd.strip():
                c.execute(text(cmd))
    csv = ("data,esp_long,esp_short,esp_net,com_long,com_short,com_net,idx_long,"
           "idx_short,idx_net,open_interest,produto,fonte\n"
           "2026-07-15,100,50,50,200,300,-100,80,20,60,1000,SUGAR NO. 11,CFTC\n")
    _prep(monkeypatch, csv)
    r = m.CftcSugarCollector().run()
    assert r.ok
    assert r.rows_new == 1


def test_enso_parse(monkeypatch):
    csv = ("data_coleta,alert_status,fase_oni_atual,trimestre_oni_atual,"
           "oni_anom_atual_C,nino34_weekly_C,window1_periodo,window1_pct,"
           "window2_periodo,window2_pct,sinopse,fonte_oni_url,fonte_ensodisc_url\n"
           "2026-07-18,El Niño Advisory,Neutro,AMJ 2026,0.98,1.2,,,,,texto,url1,url2\n")
    _prep(monkeypatch, csv)
    r = m.EnsoCollector().run()
    assert r.ok
