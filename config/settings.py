"""Configuração central da aplicação (Pydantic Settings).

Lê variáveis de ambiente / .env. Nenhum segredo é embutido no código.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    database_url_ro: str = ""

    resend_api_key: str = ""
    email_from: str = ""
    email_test_recipient: str = ""

    summary_provider: str = "extractive"
    summary_api_key: str = ""

    timezone: str = "America/Sao_Paulo"
    env: str = "local"

    @property
    def sqlalchemy_url(self) -> str:
        """URL de escrita. Cai em SQLite local quando DATABASE_URL não está definida."""
        return self.database_url or f"sqlite:///{ROOT / 'canavis.db'}"

    @property
    def sqlalchemy_url_ro(self) -> str:
        """URL de leitura usada pelo app (separa leitura de escrita quando configurado)."""
        return self.database_url_ro or self.sqlalchemy_url


settings = Settings()
