-- 0012_raiox_base_teste.sql -- base de TESTE do Raio X (so dados ficticios).
-- Guarda uma carteira serializada em JSON, so para testes. A tela sempre avisa.
CREATE TABLE IF NOT EXISTS raiox_base_teste (
    id             TEXT PRIMARY KEY,
    dados_json     TEXT NOT NULL,
    linhas         INTEGER NOT NULL,
    salvo_em       TIMESTAMP NOT NULL,
    salvo_por      TEXT
);
