"""Contrato comum dos coletores.

Cada fonte implementa um adaptador isolado com a mesma interface, para que
possa ser trocada sem afetar o resto do sistema. O fluxo é sempre:
fetch -> parse -> normalize -> validate -> upsert, com registro de execução.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.models import CollectorResult, IndicatorValue
from src.persistence.repositories import log_run, upsert_indicator_values


class Collector(ABC):
    source_code: str
    version: str = "0.1.0"

    @abstractmethod
    def collect(self) -> list[IndicatorValue]:
        """Busca, parseia e normaliza os valores. Não toca no banco."""

    def run(self) -> CollectorResult:
        """Executa a coleta e persiste de forma idempotente, registrando a saúde."""
        started = datetime.utcnow()
        try:
            values = self.collect()
            new = upsert_indicator_values(values)
            result = CollectorResult(
                source_code=self.source_code,
                started_at=started,
                finished_at=datetime.utcnow(),
                rows_seen=len(values),
                rows_new=new,
                ok=True,
            )
        except Exception as exc:  # noqa: BLE001 — falha de fonte não derruba o job
            result = CollectorResult(
                source_code=self.source_code,
                started_at=started,
                finished_at=datetime.utcnow(),
                ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        log_run(result)
        return result
