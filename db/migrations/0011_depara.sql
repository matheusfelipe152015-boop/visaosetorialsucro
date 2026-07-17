-- 0011_depara.sql — de-para editável (mapa cliente -> analista/setor/ativo).
--
-- Diferente da carteira, o de-para PODE ser salvo: é só um mapa de configuração,
-- sem dado sensível de crédito. Fica ligado ao ID do cliente. Editável no app.

CREATE TABLE IF NOT EXISTS depara (
    id_cliente       TEXT PRIMARY KEY,
    grupo            TEXT,
    analista         TEXT,
    setor_gerencial  TEXT,
    ativo            INTEGER NOT NULL DEFAULT 1,   -- 1 = ativo, 0 = inativo
    atualizado_em    TIMESTAMP NOT NULL,
    atualizado_por   TEXT
);
