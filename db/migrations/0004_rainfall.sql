-- 0004_rainfall.sql — chuva por estado e período.
-- Guarda precipitação observada (mm) e a média histórica (normal) por UF,
-- em diferentes janelas (semanal/mensal/trimestral). Portátil SQLite/PostgreSQL.

CREATE TABLE IF NOT EXISTS rainfall (
    id               TEXT PRIMARY KEY,
    source_code      TEXT REFERENCES sources(code),
    uf               TEXT NOT NULL,
    regiao           TEXT,
    periodo          TEXT NOT NULL,            -- semanal | mensal | trimestral
    data_referencia  DATE NOT NULL,
    mm               DOUBLE PRECISION NOT NULL,-- chuva acumulada observada
    normal_mm        DOUBLE PRECISION,         -- média histórica para o período
    data_coleta      TIMESTAMP NOT NULL,
    collector_version TEXT,
    status_validacao TEXT DEFAULT 'ok',
    UNIQUE (uf, periodo, data_referencia, source_code)
);

CREATE INDEX IF NOT EXISTS ix_rain_periodo ON rainfall (periodo, data_referencia);
