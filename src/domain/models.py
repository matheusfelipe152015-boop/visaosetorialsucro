"""Modelos de domínio (Pydantic).

Todo registro coletado carrega rastreabilidade: fonte, URL, data de referência,
data de publicação, data de coleta, hash, versão do coletor, unidade/moeda/escala.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime

from pydantic import BaseModel, Field

from .enums import ValidationStatus


class IndicatorValue(BaseModel):
    indicator_code: str
    source_code: str
    data_referencia: date
    valor: float
    unidade: str
    moeda: str | None = None
    escala: str | None = None
    data_publicacao: date | None = None
    data_coleta: datetime = Field(default_factory=datetime.utcnow)
    collector_version: str = "0.1.0"
    status_validacao: ValidationStatus = ValidationStatus.OK
    url_original: str | None = None

    @property
    def hash(self) -> str:
        """Checksum determinístico — base da idempotência e da deduplicação."""
        raw = (
            f"{self.indicator_code}|{self.source_code}|{self.data_referencia}"
            f"|{self.valor}|{self.unidade}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class CollectorResult(BaseModel):
    """Resultado de uma execução de coletor (alimenta a página de Saúde)."""

    source_code: str
    started_at: datetime
    finished_at: datetime
    rows_seen: int = 0
    rows_new: int = 0
    ok: bool = True
    error: str | None = None

    @property
    def duration_s(self) -> float:
        return (self.finished_at - self.started_at).total_seconds()
