-- 0009_usuarios.sql — contas individuais (email + senha), com níveis e aprovação.
--
-- Níveis (papel): 'adm', 'gerencia', 'analista'.
-- Situação: 'pendente' (aguardando aprovação) ou 'ativo'.
-- A senha NUNCA é guardada em texto: guardamos o hash PBKDF2 + o "sal".
-- Portátil SQLite/PostgreSQL.

CREATE TABLE IF NOT EXISTS usuarios (
    id             TEXT PRIMARY KEY,
    email          TEXT NOT NULL UNIQUE,
    nome           TEXT,
    senha_hash     TEXT NOT NULL,
    senha_sal      TEXT NOT NULL,
    papel          TEXT NOT NULL DEFAULT 'analista',
    situacao       TEXT NOT NULL DEFAULT 'pendente',
    criado_em      TIMESTAMP NOT NULL,
    aprovado_em    TIMESTAMP,
    aprovado_por   TEXT
);

CREATE INDEX IF NOT EXISTS ix_usuarios_situacao ON usuarios (situacao);
