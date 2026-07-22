-- 0015_mercado_series.sql — séries de mercado do sugar-intel (visões da aba Mercado)

-- CFTC: posicionamento de fundos no açúcar NY11 (semanal)
CREATE TABLE IF NOT EXISTS cftc_sugar (
    id             TEXT PRIMARY KEY,
    data_ref       DATE NOT NULL UNIQUE,
    esp_net        DOUBLE PRECISION,   -- posição líquida especulativa
    com_net        DOUBLE PRECISION,   -- posição líquida comercial (hedgers)
    idx_net        DOUBLE PRECISION,   -- fundos indexados
    open_interest  DOUBLE PRECISION,
    data_coleta    TIMESTAMP NOT NULL
);

-- Curva a termo do açúcar NY11 (preço de fechamento por vencimento)
CREATE TABLE IF NOT EXISTS ny11_curva (
    id             TEXT PRIMARY KEY,
    vencimento     TEXT NOT NULL,      -- ex.: SBN26
    mes_nome       TEXT,
    ano_venc       INTEGER,
    data_ref       DATE NOT NULL,
    close_clb      DOUBLE PRECISION,   -- fechamento em cents/lb
    data_coleta    TIMESTAMP NOT NULL,
    UNIQUE (vencimento, data_ref)
);

-- Basis: ESALQ vs NY equivalente em R$/sc (paridade de exportação)
CREATE TABLE IF NOT EXISTS basis_acucar (
    id                 TEXT PRIMARY KEY,
    data_ref           DATE NOT NULL UNIQUE,
    esalq_rs_sc50kg    DOUBLE PRECISION,
    ny_equiv_rs_sc50kg DOUBLE PRECISION,
    ny_cont_clb        DOUBLE PRECISION,
    usd_ptax           DOUBLE PRECISION,
    data_coleta        TIMESTAMP NOT NULL
);

-- Performance de ativos (finviz) — snapshot mais recente
CREATE TABLE IF NOT EXISTS finviz_perf (
    id            TEXT PRIMARY KEY,
    data_coleta   DATE NOT NULL,
    ticker        TEXT NOT NULL,
    nome          TEXT,
    categoria     TEXT,
    perf_1w       DOUBLE PRECISION,
    perf_1m       DOUBLE PRECISION,
    perf_ytd      DOUBLE PRECISION,
    perf_1y       DOUBLE PRECISION,
    UNIQUE (ticker, data_coleta)
);

-- ENSO (El Niño) — snapshot mais recente
CREATE TABLE IF NOT EXISTS enso_status (
    id                TEXT PRIMARY KEY,
    data_coleta       DATE NOT NULL UNIQUE,
    alert_status      TEXT,
    fase_oni          TEXT,
    trimestre_oni     TEXT,
    oni_anom_c        DOUBLE PRECISION,
    nino34_c          DOUBLE PRECISION,
    sinopse           TEXT
);
