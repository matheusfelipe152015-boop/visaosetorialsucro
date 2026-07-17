"""Formatação de números para exibição (padrão brasileiro, sem notação científica).

Resolve o problema de `f"{709100:.4g}"` virar "7.091e+05" (ilegível) e de
unidades já escaladas ("mil t") ganharem escala em cima ("44 mil mil t").
"""

from __future__ import annotations


def _br(valor: float, casas: int) -> str:
    """Ponto de milhar e vírgula decimal (padrão BR), sem zeros pendurados."""
    s = f"{valor:,.{casas}f}"
    s = s.replace(",", "·").replace(".", ",").replace("·", ".")
    if "," in s:  # tira zeros à direita: '71,20' -> '71,2' | '5,00' -> '5'
        s = s.rstrip("0").rstrip(",")
    return s


def fmt_valor(valor: float | int | None) -> str:
    """Número legível, com escala automática para valores grandes."""
    if valor is None:
        return "—"
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "—"
    if v != v:  # NaN
        return "—"

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
    return f"−{txt}" if negativo else txt


def fmt_indicador(valor, unidade: str | None) -> tuple[str, str]:
    """Formata valor + unidade juntos, evitando escala duplicada.

    Unidades já escaladas ('mil t', 'mil L', 'mil ha') são convertidas para a
    unidade base, e a escala vai para o número:
        709100 'mil t'  -> ('709,1 mi', 't')
        29260000 'mil L'-> ('29,3 bi', 'L')
    """
    u = (unidade or "").strip()
    if u.lower().startswith("mil ") and valor is not None:
        try:
            return fmt_valor(float(valor) * 1_000), u[4:]
        except (TypeError, ValueError):
            pass
    return fmt_valor(valor), u


def fmt_moeda_mil(valor) -> str:
    """Valor em R$ mil (como vem da CVM) -> reais legíveis. 7431765 -> 'R$ 7,4 bi'."""
    if valor is None:
        return "—"
    try:
        reais = float(valor) * 1_000
    except (TypeError, ValueError):
        return "—"
    if reais != reais:
        return "—"
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
    return f"−{txt}" if negativo else txt
