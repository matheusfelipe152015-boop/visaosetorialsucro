-- 0019_petrobras_reajustes.sql — reajustes de preço da Petrobras nas refinarias

CREATE TABLE IF NOT EXISTS petrobras_reajustes (
    id                 TEXT PRIMARY KEY,
    data_ref           DATE NOT NULL,
    produto            TEXT NOT NULL,
    tipo               TEXT,
    preco_anterior_rs_l DOUBLE PRECISION,
    preco_novo_rs_l    DOUBLE PRECISION,
    delta_rs_l         DOUBLE PRECISION,
    delta_pct          DOUBLE PRECISION,
    descricao          TEXT,
    data_coleta        TIMESTAMP NOT NULL,
    UNIQUE (data_ref, produto)
);
