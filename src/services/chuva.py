"""Agregação de chuva por estado e região (funções puras, testáveis).

O dado bruto vem por estação meteorológica (INMET). O coletor agrega para
chuva acumulada por estado. Aqui ficam as funções que:
  - somam/agregam estados em regiões;
  - calculam a anomalia (comparação com a média histórica/normal).

UF -> Região (padrão IBGE).
"""

from __future__ import annotations

REGIAO_POR_UF: dict[str, str] = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]

# Estados da região canavieira do Centro-Sul (referência para o setor).
CENTRO_SUL = {"SP", "MG", "GO", "MS", "MT", "PR", "RJ", "ES"}


def regiao_da_uf(uf: str) -> str | None:
    return REGIAO_POR_UF.get(uf.upper())


def chuva_por_regiao(por_uf: dict[str, float]) -> dict[str, float]:
    """Agrega a chuva (mm) dos estados para o total/médio por região.

    Usamos a MÉDIA dos estados da região (mm é uma grandeza por área, então a
    média representa melhor 'o quanto choveu na região' do que a soma).
    """
    acc: dict[str, list[float]] = {r: [] for r in REGIOES}
    for uf, mm in por_uf.items():
        reg = regiao_da_uf(uf)
        if reg:
            acc[reg].append(mm)
    return {r: round(sum(v) / len(v), 1) for r, v in acc.items() if v}


def anomalia(observado: float, normal: float) -> float | None:
    """Diferença percentual em relação à média histórica (normal).

    Ex.: observado 120mm, normal 100mm -> +20% (choveu acima do normal).
    """
    if not normal:
        return None
    return round((observado / normal - 1) * 100, 1)


def classifica_anomalia(pct: float | None) -> str:
    """Rótulo curto para a anomalia."""
    if pct is None:
        return "sem referência"
    if pct >= 20:
        return "muito acima do normal"
    if pct >= 5:
        return "acima do normal"
    if pct > -5:
        return "dentro do normal"
    if pct > -20:
        return "abaixo do normal"
    return "muito abaixo do normal"
