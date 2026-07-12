-- 0006_safra_uf.sql — safra de cana por estado (CONAB).
CREATE TABLE IF NOT EXISTS safra_uf (
    id               TEXT PRIMARY KEY,
    uf               TEXT NOT NULL,
    regiao           TEXT,
    safra            TEXT NOT NULL,
    metric           TEXT NOT NULL,
    valor            DOUBLE PRECISION NOT NULL,
    unidade          TEXT,
    data_referencia  DATE,
    source_code      TEXT,
    data_coleta      TIMESTAMP NOT NULL,
    collector_version TEXT,
    url_original     TEXT,
    UNIQUE (uf, safra, metric, source_code)
);

CREATE INDEX IF NOT EXISTS ix_safra_uf_metric ON safra_uf (metric, safra);
CREATE INDEX IF NOT EXISTS ix_safra_uf_uf ON safra_uf (uf);
