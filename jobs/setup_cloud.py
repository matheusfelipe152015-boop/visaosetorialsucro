"""Prepara o banco na nuvem (Supabase) de uma vez.

O que faz, em ordem:
  1. confere se há um DATABASE_URL configurado (senão, avisa e para);
  2. cria todas as tabelas (roda as migrações);
  3. cadastra o catálogo de fontes e indicadores (sem inserir valores).

Uso:
    # 1. coloque a connection string do Supabase no .env (DATABASE_URL=...)
    # 2. rode:
    python jobs/setup_cloud.py

Depois disto, rode `python jobs/run_daily.py` para a primeira coleta real,
ou deixe o agendador (GitHub Actions) cuidar disso diariamente.

É seguro rodar mais de uma vez: tabelas e catálogo são idempotentes.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import settings
from src.catalog import register_catalog
from src.persistence.db import get_engine, init_schema


def main() -> None:
    url = settings.database_url
    if not url:
        print("✗ DATABASE_URL não está configurado.")
        print("  Abra o arquivo .env e cole a connection string do Supabase em DATABASE_URL.")
        print("  (Veja o passo a passo em docs/SUPABASE.md.)")
        sys.exit(1)

    # esconde a senha ao exibir, por segurança
    mascarado = url
    if "@" in url and "//" in url:
        prefixo, resto = url.split("//", 1)
        if "@" in resto:
            cred, host = resto.split("@", 1)
            user = cred.split(":", 1)[0]
            mascarado = f"{prefixo}//{user}:****@{host}"
    print(f"→ Conectando em: {mascarado}")

    backend = get_engine().url.get_backend_name()
    if backend == "sqlite":
        print("⚠  Atenção: isto está apontando para SQLite local, não para a nuvem.")
        print("   Confira o DATABASE_URL no .env (deve começar com postgresql+psycopg://).")
        sys.exit(1)

    print("→ Criando tabelas (migrações)…")
    init_schema()

    print("→ Cadastrando catálogo de fontes e indicadores…")
    with get_engine().begin() as conn:
        register_catalog(conn)

    print("\n✓ Banco na nuvem pronto!")
    print("  Próximo passo: `python jobs/run_daily.py` para a primeira coleta real.")


if __name__ == "__main__":
    main()
