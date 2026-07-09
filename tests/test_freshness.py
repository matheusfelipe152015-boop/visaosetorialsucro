"""Testa o cálculo de frescor."""

from datetime import date

from src.domain.enums import Frequency, FreshnessStatus
from src.domain.freshness import freshness_status

TODAY = date(2026, 6, 21)


def test_daily_fresh():
    assert freshness_status(date(2026, 6, 20), Frequency.DAILY, today=TODAY) == FreshnessStatus.ATUALIZADO


def test_daily_attention():
    assert freshness_status(date(2026, 6, 18), Frequency.DAILY, today=TODAY) == FreshnessStatus.ATENCAO


def test_daily_stale():
    assert freshness_status(date(2026, 6, 10), Frequency.DAILY, today=TODAY) == FreshnessStatus.DESATUALIZADO


def test_source_unavailable_overrides():
    s = freshness_status(date(2026, 6, 20), Frequency.DAILY, source_available=False, today=TODAY)
    assert s == FreshnessStatus.INDISPONIVEL


def test_unknown_frequency():
    assert freshness_status(date(2026, 6, 20), Frequency.UNKNOWN, today=TODAY) == FreshnessStatus.DESCONHECIDA
