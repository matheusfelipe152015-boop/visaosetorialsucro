"""Formatacao de numeros para exibicao (padrao brasileiro, sem notacao cientifica)."""

from __future__ import annotations


def _br(valor, casas):
    s = f"{valor:,.{casas}f}"
    s = s.replace(",", "\u00b7").replace(".", ",").replace("\u00b7", ".")
    if "," in s:
        s = s.rstrip("0").rstrip(",")
    return s


def fmt_valor(valor):
    """Numero legivel, com escala automatica para valores grandes."""
    if valor is None:
        return "\u2014"
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "\u2014"
    if v != v:
        return "\u2014"

    negativo = v < 0
    a = abs(v)

    if a >= 1_000_000_000:
        txt = f"{_br(a / 1_000_000_000, 1)} bi"
    elif a >= 1_000_000:
        txt = f"{_br(a / 1_000_000, 1)} mi"
    elif a >= 10_000:
        txt = f"{_br(a / 1_000, 1)} mil"
    elif a >= 100:
        txt = _br(a, 1)
    elif a >= 1:
        txt = _br(a, 2)
    else:
        txt = _br(a, 3)
    return f"\u2212{txt}" if negativo else txt


def fmt_indicador(valor, unidade):
    """Evita escala duplicada: 709100 'mil t' -> ('709,1 mi', 't')."""
    u = (unidade or "").strip()
    if u.lower().startswith("mil ") and valor is not None:
        try:
            return fmt_valor(float(valor) * 1_000), u[4:]
        except (TypeError, ValueError):
            pass
    return fmt_valor(valor), u


def fmt_moeda_mil(valor):
    """Valor em R$ mil (CVM) -> reais legiveis. 7431765 -> 'R$ 7,4 bi'."""
    if valor is None:
        return "\u2014"
    try:
        reais = float(valor) * 1_000
    except (TypeError, ValueError):
        return "\u2014"
    if reais != reais:
        return "\u2014"
    negativo = reais < 0
    a = abs(reais)
    if a >= 1_000_000_000:
        txt = f"R$ {_br(a / 1_000_000_000, 1)} bi"
    elif a >= 1_000_000:
        txt = f"R$ {_br(a / 1_000_000, 1)} mi"
    elif a >= 1_000:
        txt = f"R$ {_br(a / 1_000, 1)} mil"
    else:
        txt = f"R$ {_br(a, 2)}"
    return f"\u2212{txt}" if negativo else txt
