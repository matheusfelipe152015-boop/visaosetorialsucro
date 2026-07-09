"""Enums de domínio."""

from __future__ import annotations

from enum import StrEnum


class Frequency(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    EVENTUAL = "eventual"
    UNKNOWN = "unknown"


class FreshnessStatus(StrEnum):
    """Status de frescor exibido em todo card (assinatura visual do produto)."""

    ATUALIZADO = "Atualizado"
    ATENCAO = "Atenção"
    DESATUALIZADO = "Desatualizado"
    INDISPONIVEL = "Fonte indisponível"
    DESCONHECIDA = "Frequência desconhecida"
    MANUAL = "Coleta manual"
    EM_VALIDACAO = "Em validação"


class ValidationStatus(StrEnum):
    OK = "ok"
    PENDING = "pending"
    FAILED = "failed"
