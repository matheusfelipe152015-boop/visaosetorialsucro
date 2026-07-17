-- 0010_raiox_comentarios.sql — comentários/status do Raio X, atrelados ao ID do cliente.
--
-- IMPORTANTE (privacidade): aqui NÃO guardamos a carteira de crédito. Só o texto do
-- comentário e o status, ligados ao ID do cliente. A carteira (limites, riscos,
-- ratings) vive apenas na sessão e nunca é gravada. Quando o usuário sobe a base de
-- novo, o comentário reencontra o cliente pelo ID.

CREATE TABLE IF NOT EXISTS raiox_comentarios (
    id_cliente     TEXT PRIMARY KEY,
    status         TEXT,
    comentario     TEXT,
    atualizado_em  TIMESTAMP NOT NULL,
    atualizado_por TEXT
);
