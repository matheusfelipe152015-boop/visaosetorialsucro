-- 0002_news_filters.sql — metadados para filtragem de notícias.
-- ALTER ... ADD COLUMN é portátil (SQLite e PostgreSQL). O runner de migrações
-- tolera reexecução (ignora erro de coluna já existente).

ALTER TABLE news_articles ADD COLUMN regiao TEXT;
ALTER TABLE news_articles ADD COLUMN segmento TEXT;
