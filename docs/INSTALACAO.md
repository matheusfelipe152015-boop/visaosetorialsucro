# Instalação e execução

Pré-requisitos: Python 3.12+ (testado em macOS Apple Silicon).

## 1. Ambiente

```bash
cd canavis
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # instala app + ferramentas de teste
cp .env.example .env             # ajuste se for usar Supabase/Resend
```

Sem `DATABASE_URL` no `.env`, o projeto usa um **SQLite local** (`canavis.db`) —
ideal para rodar tudo na sua máquina sem depender de nuvem.

## 2. Popular dados para ver o app

```bash
python db/seeds/seed_demo.py     # dados de DEMONSTRAÇÃO (sinalizados na tela)
```

ou já trazer o câmbio real do Banco Central:

```bash
python jobs/run_daily.py         # coleta USD/BRL (BCB SGS série 1)
```

## 3. Abrir a interface

```bash
streamlit run app/Home.py
```

Páginas: **Visão executiva** (Home), **Mercado** (câmbio PTAX com gráfico e
metadados de rastreabilidade) e **Saúde dos dados** (situação de cada fonte).

## 4. Testes

```bash
pytest -q        # 8 testes: parse do PTAX, frescor, idempotência
ruff check .     # lint
```

## 5. Migrar para Supabase (quando quiser)

1. Crie o projeto no Supabase e pegue a connection string (porta 6543, pooler).
2. Preencha `DATABASE_URL=postgresql+psycopg://...` no `.env`.
3. O mesmo `db/migrations/0001_init.sql` roda no PostgreSQL — não há troca de código.
