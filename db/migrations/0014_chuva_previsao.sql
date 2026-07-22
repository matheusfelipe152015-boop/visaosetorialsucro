-- 0014_chuva_previsao.sql -- previsao de chuva 14 dias por cidade (Open-Meteo).
-- Complementa a tabela rainfall (que guarda observado): esta guarda a PREVISAO.
CREATE TABLE IF NOT EXISTS chuva_previsao (
    id            TEXT PRIMARY KEY,
    cidade        TEXT NOT NULL,
    data_prev     DATE NOT NULL,
    precip_mm     DOUBLE PRECISION NOT NULL,
    lat           DOUBLE PRECISION,
    lon           DOUBLE PRECISION,
    data_coleta   DATE NOT NULL,
    fonte_url     TEXT,
    UNIQUE (cidade, data_prev)
);
