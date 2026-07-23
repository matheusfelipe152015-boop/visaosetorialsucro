-- 0016_etanol_series.sql — bloco Etanol (sugar-intel): B3, base SP-GO, ABICOM

-- Curva forward do etanol hidratado na B3 (ajustes por vencimento)
CREATE TABLE IF NOT EXISTS b3_eth_curva (
    id               TEXT PRIMARY KEY,
    data_ref         DATE NOT NULL,
    vencimento       TEXT NOT NULL,
    ajuste           DOUBLE PRECISION,
    volume           DOUBLE PRECISION,
    contratos_aberto DOUBLE PRECISION,
    data_coleta      TIMESTAMP NOT NULL,
    UNIQUE (vencimento, data_ref)
);

-- Base do hidratado: usina SP menos GO (R$/L), semanal
CREATE TABLE IF NOT EXISTS etanol_base_sp_go (
    id             TEXT PRIMARY KEY,
    semana_inicio  DATE NOT NULL UNIQUE,
    sp_rs_l        DOUBLE PRECISION,
    go_rs_l        DOUBLE PRECISION,
    base_rs_l      DOUBLE PRECISION,
    data_coleta    TIMESTAMP NOT NULL
);

-- ABICOM: defasagem da paridade de importação (diesel e gasolina)
CREATE TABLE IF NOT EXISTS abicom_ppi (
    id                     TEXT PRIMARY KEY,
    data_ref               DATE NOT NULL UNIQUE,
    defasagem_diesel_pct   DOUBLE PRECISION,
    defasagem_gasolina_pct DOUBLE PRECISION,
    ptax_brl_usd           DOUBLE PRECISION,
    brent_usd_bbl          DOUBLE PRECISION,
    data_coleta            TIMESTAMP NOT NULL
);
