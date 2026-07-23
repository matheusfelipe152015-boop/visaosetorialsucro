-- 0017_unica_snd.sql — UNICA: oferta x demanda mensal de etanol (Centro-Sul)
-- Formato longo: uma linha por série/safra/mês. As séries incluem entradas
-- (produção), saídas (vendas), estoque acumulado, moagem, açúcar, mix, ATR e chuva.

CREATE TABLE IF NOT EXISTS unica_snd (
    id           TEXT PRIMARY KEY,
    serie        TEXT NOT NULL,
    safra        TEXT NOT NULL,
    data_ref     DATE NOT NULL,
    valor        DOUBLE PRECISION,
    data_coleta  TIMESTAMP NOT NULL,
    UNIQUE (serie, safra, data_ref)
);
