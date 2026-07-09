"""Paridade etanol/gasolina (função pura, testável).

A paridade é a razão entre o preço do etanol e o da gasolina. A regra prática
do mercado: até ~70% o etanol compensa para o consumidor; acima disso, a
gasolina leva vantagem. É um indicador central para a demanda de etanol e,
portanto, para o setor sucroenergético.
"""

from __future__ import annotations

LIMITE_VANTAGEM = 0.70  # etanol compensa abaixo deste patamar


def paridade(preco_etanol: float, preco_gasolina: float) -> float | None:
    """Razão etanol/gasolina (ex.: 0.68 = etanol a 68% do preço da gasolina)."""
    if not preco_gasolina:
        return None
    return preco_etanol / preco_gasolina


def etanol_compensa(preco_etanol: float, preco_gasolina: float) -> bool | None:
    """True se o etanol vale a pena (paridade abaixo do limite de 70%)."""
    p = paridade(preco_etanol, preco_gasolina)
    if p is None:
        return None
    return p < LIMITE_VANTAGEM


def leitura_paridade(preco_etanol: float, preco_gasolina: float) -> str:
    """Texto curto para exibição."""
    p = paridade(preco_etanol, preco_gasolina)
    if p is None:
        return "—"
    pct = p * 100
    if p < LIMITE_VANTAGEM:
        return f"{pct:.1f}% — etanol compensa"
    return f"{pct:.1f}% — gasolina compensa"
