-- 0005_company_metrics.sql — indicadores operacionais e financeiros por empresa.
-- Cada linha: um indicador (ex.: moagem) de uma empresa, num período/safra,
-- com rastreabilidade (de onde veio, quando foi divulgado, quando coletamos).
-- Portátil SQLite/PostgreSQL.

CREATE TABLE IF NOT EXISTS company_metrics (
    id               TEXT PRIMARY KEY,
    company_code     TEXT REFERENCES companies(code),
    metric           TEXT NOT NULL,    -- moagem | mix_acucar | mix_etanol | atr | prod_acucar | prod_etanol | receita | divida_liquida | ebitda
    grupo            TEXT,             -- operacional | financeiro
    safra            TEXT,             -- ex.: 2025/26
    periodo          TEXT,             -- ex.: 3T26 | safra
    data_referencia  DATE,
    valor            DOUBLE PRECISION NOT NULL,
    unidade          TEXT,
    fonte            TEXT,             -- release_producao | cvm_dfp | cvm_itr
    data_publicacao  DATE,
    data_coleta      TIMESTAMP NOT NULL,
    collector_version TEXT,
    status_validacao TEXT DEFAULT 'ok',
    url_original     TEXT,
    UNIQUE (company_code, metric, periodo, fonte)
);

CREATE INDEX IF NOT EXISTS ix_cm_metric ON company_metrics (metric, periodo);
CREATE INDEX IF NOT EXISTS ix_cm_company ON company_metrics (company_code);
