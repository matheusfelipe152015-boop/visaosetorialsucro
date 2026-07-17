-- 0006_safra_uf.sql — safra de cana por estado (CONAB).
-- Uma linha por UF × safra × métrica. Portátil SQLite/PostgreSQL.

CREATE TABLE IF NOT EXISTS safra_uf (
    id               TEXT PRIMARY KEY,
    uf               TEXT NOT NULL,
    regiao           TEXT,
    safra            TEXT NOT NULL,        -- ex.: 2025/26
    metric           TEXT NOT NULL,        -- cana_producao | acucar_producao | etanol_producao | area_plantada | atr
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
