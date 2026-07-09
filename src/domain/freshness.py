"""Cálculo de frescor: data de referência + frequência esperada -> status.

Regra central do produto: nunca apresentar dado antigo como atual. Cada
indicador/fonte tem uma frequência esperada; comparamos a idade do dado (em
dias úteis aproximados) contra limites de "atualizado" e "atenção".
"""

from __future__ import annotations

from datetime import date

from .enums import Frequency, FreshnessStatus

# (limite_atualizado, limite_atencao) em dias corridos por frequência.
# Acima do limite de atenção => Desatualizado.
_THRESHOLDS: dict[Frequency, tuple[int, int]] = {
    Frequency.DAILY: (2, 4),
    Frequency.WEEKLY: (8, 14),
    Frequency.BIWEEKLY: (18, 30),
    Frequency.MONTHLY: (38, 55),
    Frequency.EVENTUAL: (10_000, 10_000),  # nunca "vence" sozinho
}


def freshness_status(
    data_referencia: date | None,
    frequency: Frequency,
    *,
    source_available: bool = True,
    today: date | None = None,
) -> FreshnessStatus:
    if not source_available:
        return FreshnessStatus.INDISPONIVEL
    if frequency == Frequency.UNKNOWN:
        return FreshnessStatus.DESCONHECIDA
    if data_referencia is None:
        return FreshnessStatus.EM_VALIDACAO

    today = today or date.today()
    age = (today - data_referencia).days
    fresh_lim, warn_lim = _THRESHOLDS.get(frequency, (10_000, 10_000))

    if age <= fresh_lim:
        return FreshnessStatus.ATUALIZADO
    if age <= warn_lim:
        return FreshnessStatus.ATENCAO
    return FreshnessStatus.DESATUALIZADO


# Mapa status -> classe de cor (consumido pelo tema do app).
STATUS_TONE: dict[FreshnessStatus, str] = {
    FreshnessStatus.ATUALIZADO: "ok",
    FreshnessStatus.ATENCAO: "warn",
    FreshnessStatus.DESATUALIZADO: "old",
    FreshnessStatus.INDISPONIVEL: "off",
    FreshnessStatus.DESCONHECIDA: "off",
    FreshnessStatus.MANUAL: "warn",
    FreshnessStatus.EM_VALIDACAO: "warn",
}
