"""Leitura agregada do setor a partir dos dados das empresas (funções puras).

Junta os números operacionais divulgados pelas usinas de capital aberto para
responder perguntas de panorama: a moagem do conjunto está subindo ou caindo?
Como está o mix médio (açúcar × etanol)?

Trabalha sobre listas de dicionários simples (fáceis de testar), no formato:
    {"company": "sao_martinho", "metric": "moagem", "valor": 24.1, "periodo": "3T26"}
"""

from __future__ import annotations


def soma_metric(registros: list[dict], metric: str, periodo: str | None = None) -> float:
    """Soma o valor de uma métrica entre empresas (opcionalmente filtrando período)."""
    total = 0.0
    for r in registros:
        if r["metric"] == metric and (periodo is None or r.get("periodo") == periodo):
            total += r["valor"]
    return round(total, 2)


def variacao_pct(atual: float, anterior: float) -> float | None:
    """Variação percentual entre dois períodos."""
    if not anterior:
        return None
    return round((atual / anterior - 1) * 100, 1)


def tendencia(pct: float | None) -> str:
    """Rótulo de direção para a leitura agregada."""
    if pct is None:
        return "sem referência"
    if pct > 1.5:
        return "em alta"
    if pct < -1.5:
        return "em queda"
    return "estável"


def mix_medio(registros: list[dict], periodo: str | None = None) -> dict[str, float] | None:
    """Mix médio açúcar/etanol do conjunto (média simples dos percentuais informados).

    Espera métricas 'mix_acucar' e 'mix_etanol' em pontos percentuais.
    """
    acucar = [
        r["valor"] for r in registros
        if r["metric"] == "mix_acucar" and (periodo is None or r.get("periodo") == periodo)
    ]
    etanol = [
        r["valor"] for r in registros
        if r["metric"] == "mix_etanol" and (periodo is None or r.get("periodo") == periodo)
    ]
    if not acucar or not etanol:
        return None
    return {
        "acucar": round(sum(acucar) / len(acucar), 1),
        "etanol": round(sum(etanol) / len(etanol), 1),
    }
