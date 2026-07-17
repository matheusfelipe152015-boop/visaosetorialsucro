-- 0007_metricas_uf.sql — métricas por estado (genérica).
-- Serve para qualquer dado por UF que não seja safra: preços da ANP,
-- paridade etanol/gasolina, e futuras séries por estado.
-- 'periodo' é texto livre (ex.: '2026-06' para mês). Portátil SQLite/PostgreSQL.

CREATE TABLE IF NOT EXISTS metricas_uf (
    id               TEXT PRIMARY KEY,
    uf               TEXT NOT NULL,
    regiao           TEXT,
    periodo          TEXT NOT NULL,
    metric           TEXT NOT NULL,
    valor            DOUBLE PRECISION NOT NULL,
    unidade          TEXT,
    data_referencia  DATE,
    source_code      TEXT,
    data_coleta      TIMESTAMP NOT NULL,
    collector_version TEXT,
    status_validacao TEXT,
    url_original     TEXT,
    UNIQUE (uf, periodo, metric, source_code)
);

CREATE INDEX IF NOT EXISTS ix_metricas_uf_metric ON metricas_uf (metric, periodo);
CREATE INDEX IF NOT EXISTS ix_metricas_uf_uf ON metricas_uf (uf);
