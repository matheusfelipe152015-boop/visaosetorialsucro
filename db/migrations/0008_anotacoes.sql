-- 0008_anotacoes.sql — anotacoes/registros do usuario.
CREATE TABLE IF NOT EXISTS anotacoes (
    id              TEXT PRIMARY KEY,
    titulo          TEXT NOT NULL,
    conteudo        TEXT NOT NULL,
    criada_em       TIMESTAMP NOT NULL,
    atualizada_em   TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_anotacoes_atualizada ON anotacoes (atualizada_em DESC);
