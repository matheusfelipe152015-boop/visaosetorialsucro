-- 0001_init.sql — modelo inicial.
-- DDL portátil: roda no SQLite (local) e no PostgreSQL/Supabase.
-- Chaves primárias são TEXT (uuid hex gerado na aplicação) para evitar
-- dependência de SERIAL/gen_random_uuid e manter a migração idêntica nos dois bancos.

CREATE TABLE IF NOT EXISTS sources (
    code                 TEXT PRIMARY KEY,
    nome                 TEXT NOT NULL,
    instituicao          TEXT,
    tier                 TEXT,            -- A | B | C | D
    tipo_acesso          TEXT,            -- api | rss | csv | scraping | manual
    licenca              TEXT,
    automacao_permitida  BOOLEAN DEFAULT true,
    frequencia_esperada  TEXT,            -- daily | weekly | biweekly | monthly | eventual | unknown
    available            BOOLEAN DEFAULT true,
    status               TEXT
);

CREATE TABLE IF NOT EXISTS indicators (
    code         TEXT PRIMARY KEY,
    nome         TEXT NOT NULL,
    categoria    TEXT,
    unidade      TEXT,
    moeda        TEXT,
    escala       TEXT,
    source_code  TEXT REFERENCES sources(code),
    frequencia   TEXT
);

CREATE TABLE IF NOT EXISTS indicator_values (
    id               TEXT PRIMARY KEY,
    indicator_code   TEXT NOT NULL REFERENCES indicators(code),
    source_code      TEXT NOT NULL REFERENCES sources(code),
    data_referencia  DATE NOT NULL,
    data_publicacao  DATE,
    data_coleta      TIMESTAMP NOT NULL,
    valor            DOUBLE PRECISION NOT NULL,
    unidade          TEXT,
    moeda            TEXT,
    escala           TEXT,
    hash             TEXT,
    collector_version TEXT,
    status_validacao TEXT DEFAULT 'ok',
    url_original     TEXT,
    UNIQUE (indicator_code, data_referencia, source_code)   -- idempotência
);

CREATE TABLE IF NOT EXISTS source_runs (
    id           TEXT PRIMARY KEY,
    source_code  TEXT NOT NULL REFERENCES sources(code),
    started_at   TIMESTAMP NOT NULL,
    finished_at  TIMESTAMP NOT NULL,
    rows_seen    INTEGER DEFAULT 0,
    rows_new     INTEGER DEFAULT 0,
    ok           BOOLEAN DEFAULT true,
    error        TEXT,
    duration_s   DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS companies (
    code         TEXT PRIMARY KEY,
    nome         TEXT NOT NULL,
    ticker       TEXT,
    classificacao TEXT,       -- publica | privada
    tier         TEXT,
    prioridade   INTEGER
);

CREATE TABLE IF NOT EXISTS news_topics (
    code TEXT PRIMARY KEY,
    nome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS news_articles (
    id               TEXT PRIMARY KEY,
    source_code      TEXT REFERENCES sources(code),
    titulo           TEXT NOT NULL,
    resumo           TEXT,
    url_original     TEXT,
    url_canonica     TEXT UNIQUE,
    data_publicacao  DATE,
    data_acontecimento DATE,
    data_coleta      TIMESTAMP,
    idioma           TEXT,
    pais             TEXT,
    hash             TEXT,
    dedup_group_id   TEXT,
    status_coleta    TEXT
);

CREATE TABLE IF NOT EXISTS article_company_mentions (
    article_id   TEXT REFERENCES news_articles(id),
    company_code TEXT REFERENCES companies(code),
    PRIMARY KEY (article_id, company_code)
);

CREATE TABLE IF NOT EXISTS article_topics (
    article_id TEXT REFERENCES news_articles(id),
    topic_code TEXT REFERENCES news_topics(code),
    PRIMARY KEY (article_id, topic_code)
);

CREATE TABLE IF NOT EXISTS watchlists (
    company_code TEXT PRIMARY KEY REFERENCES companies(code)
);

CREATE TABLE IF NOT EXISTS data_quality_events (
    id          TEXT PRIMARY KEY,
    source_code TEXT REFERENCES sources(code),
    kind        TEXT,
    message     TEXT,
    created_at  TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_values_indicator ON indicator_values (indicator_code, data_referencia);
CREATE INDEX IF NOT EXISTS ix_news_pub ON news_articles (data_publicacao);
