"""Interface de resumo desacoplada.

Modo padrão (extractive): usa o snippet/primeiras frases da fonte, sem custo e
sem risco de alucinação. O modo LLM é um plugue opcional, trocável por variável
de ambiente, e só é usado quando há chave configurada.

Trocar o provedor não exige alterar o restante do sistema.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from config.settings import settings


class Summarizer(ABC):
    @abstractmethod
    def summarize(self, *, title: str, text: str | None) -> str: ...


class ExtractiveSummarizer(Summarizer):
    """Resumo extrativo: fiel ao conteúdo, nunca cria números inexistentes."""

    def __init__(self, max_chars: int = 280) -> None:
        self.max_chars = max_chars

    def summarize(self, *, title: str, text: str | None) -> str:
        base = (text or "").strip()
        if not base:
            return "Resumo indisponível — conteúdo insuficiente. Ver fonte original."
        first = base.split(". ")
        snippet = first[0].strip()
        if len(snippet) > self.max_chars:
            snippet = snippet[: self.max_chars].rsplit(" ", 1)[0] + "…"
        return snippet


class LlmSummarizer(Summarizer):
    """Plugue opcional. Mantido desligado no MVP (sem chave => não instanciável)."""

    def __init__(self) -> None:
        if not settings.summary_api_key:
            raise RuntimeError("SUMMARY_API_KEY ausente — modo LLM desativado.")

    def summarize(self, *, title: str, text: str | None) -> str:  # pragma: no cover
        raise NotImplementedError("Plugue LLM previsto para fase 2.")


def get_summarizer() -> Summarizer:
    if settings.summary_provider == "llm":
        return LlmSummarizer()
    return ExtractiveSummarizer()
