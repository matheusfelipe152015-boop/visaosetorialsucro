-- 0013_anotacoes_imagem.sql -- permite anexar uma imagem (print) a uma anotacao.
-- A imagem fica guardada como texto base64 no proprio banco (prints ocasionais).
ALTER TABLE anotacoes ADD COLUMN imagem TEXT;
