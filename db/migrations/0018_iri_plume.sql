-- 0018_iri_plume.sql — pluma de previsão ENSO dos modelos IRI/CCSR
-- Snapshot: a cada coleta o conteúdo é substituído pela emissão mais recente.

CREATE TABLE IF NOT EXISTS iri_plume (
    id             TEXT PRIMARY KEY,
    data_coleta    DATE NOT NULL,
    emissao        TEXT,
    passo          INTEGER,
    estacao        TEXT,
    data_prev      DATE NOT NULL,
    modelo         TEXT NOT NULL,
    tipo           TEXT,
    nino34_anom_c  DOUBLE PRECISION,
    UNIQUE (modelo, data_prev)
);
