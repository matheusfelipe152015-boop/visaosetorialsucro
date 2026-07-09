-- 0003_indicator_flags.sql — marca indicadores "destaque" (KPIs do painel executivo).
-- Separa o papel de destaque da categoria do catálogo. Reexecução é tolerada pelo runner.

ALTER TABLE indicators ADD COLUMN destaque BOOLEAN DEFAULT false;
