"""Leitor de releases por palavras-chave (motor puro, testável).

Estratégia (decidida com a área de negócio): em vez de tentar entender o PDF
inteiro de cada empresa — cada uma num formato —, procuramos por rótulos
padronizados que as usinas repetem todo trimestre ("moagem", "ATR", "receita
líquida"...) e capturamos o número que aparece logo em seguida.

REGRA DE OURO: todo valor extraído assim nasce com confiabilidade "a_conferir"
e guarda o trecho original (evidência), porque o método pode errar (rótulo
ambíguo, layout novo). Nunca apresentar como verdade absoluta — sempre com o
link/treho para conferência humana.

Este módulo NÃO acessa internet nem lê PDF; recebe texto já extraído. Assim a
lógica de "achar o número certo ao lado da palavra-chave" é testável offline.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class Extracao:
    metric: str
    valor: float | None
    unidade: str | None
    rotulo_encontrado: str | None       # qual sinônimo casou
    evidencia: str | None               # trecho original (para conferência)
    confiabilidade: str = "a_conferir"  # sempre a conferir, por padrão


# Dicionário de sinônimos por indicador. Cada termo é um rótulo que costuma
# aparecer nos releases. A ordem importa: o primeiro que casar é usado.
SINONIMOS: dict[str, list[str]] = {
    "moagem": ["moagem de cana", "cana processada", "cana moida", "moagem total", "moagem"],
    "mix_acucar": ["mix de acucar", "mix acucar", "% acucar", "acucar (% do mix)"],
    "mix_etanol": ["mix de etanol", "mix etanol", "% etanol", "etanol (% do mix)"],
    "atr": ["atr", "acucar total recuperavel", "atr (kg/t)", "atr por tonelada"],
    "prod_acucar": ["producao de acucar", "acucar produzido", "producao acucar"],
    "prod_etanol": ["producao de etanol", "etanol produzido", "producao etanol"],
    "receita": ["receita liquida", "receita operacional liquida", "receita"],
    "ebitda": ["ebitda ajustado", "ebitda"],
}

# Unidades reconhecidas e como normalizá-las.
_UNIDADES = [
    ("mil ton", "mil t"), ("mil toneladas", "mil t"), ("milhoes de toneladas", "Mt"),
    ("milhao de toneladas", "Mt"), ("mt", "Mt"), ("toneladas", "t"),
    ("kg/t", "kg/t"), ("mil m3", "mil m³"), ("m3", "m³"),
    ("r$ milhoes", "R$ mi"), ("r$ mi", "R$ mi"), ("r$ bilhoes", "R$ bi"),
    ("r$ bi", "R$ bi"), ("milhoes", "mi"), ("%", "%"),
]


def _sem_acento(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()


def _parse_numero_br(token: str) -> float | None:
    """Converte número no formato BR para float.

    Regras:
      - tem vírgula -> ponto é separador de milhar, vírgula é decimal (1.234,5).
      - sem vírgula, com ponto seguido de exatamente 3 dígitos -> ponto é milhar
        (1.320 -> 1320; 1.850 -> 1850; e 12.345.678 -> 12345678).
      - sem vírgula, com ponto e nº de dígitos diferente de 3 -> ponto é decimal
        (3.5 -> 3.5).
    """
    t = token.strip().replace(" ", "")
    if not re.search(r"\d", t):
        return None
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif "." in t:
        partes = t.split(".")
        # se todos os blocos após o primeiro têm 3 dígitos -> separador de milhar
        if all(len(p) == 3 for p in partes[1:]):
            t = t.replace(".", "")
        # senão, mantém como decimal (ex.: 3.5)
    try:
        return float(t)
    except ValueError:
        return None


def extrair_metric(texto: str, metric: str) -> Extracao:
    """Procura o rótulo do indicador e captura o número logo após ele."""
    plano = _sem_acento(texto)
    for rotulo in SINONIMOS.get(metric, []):
        idx = plano.find(_sem_acento(rotulo))
        if idx == -1:
            continue
        # janela após o rótulo (até ~40 caracteres) para achar "número + unidade"
        trecho_plano = plano[idx: idx + len(rotulo) + 60]
        # captura número (formato BR ou simples), opcionalmente seguido de unidade
        apos = trecho_plano[len(rotulo):]
        m = re.search(r"(-?\d[\d.\s]*(?:,\d+)?)\s*([a-z$%/³]*\.?\s?[a-z$%/³]*)", apos)
        if not m:
            continue
        valor = _parse_numero_br(m.group(1))
        if valor is None:
            continue
        # detecta a unidade procurando termos conhecidos no trecho após o número
        pos_num = apos.find(m.group(1))
        depois = apos[pos_num + len(m.group(1)):][:25]
        unidade = None
        for chave, norm in sorted(_UNIDADES, key=lambda x: -len(x[0])):
            if depois.lstrip().startswith(chave):
                unidade = norm
                break
        # evidência: o trecho original (com acentos), aproximado
        evidencia = texto[idx: idx + len(rotulo) + 50].strip()
        return Extracao(
            metric=metric,
            valor=valor,
            unidade=unidade,
            rotulo_encontrado=rotulo,
            evidencia=evidencia,
        )
    return Extracao(metric=metric, valor=None, unidade=None, rotulo_encontrado=None, evidencia=None)


@dataclass
class ResultadoRelease:
    company_code: str
    extracoes: list[Extracao] = field(default_factory=list)

    @property
    def encontrados(self) -> int:
        return sum(1 for e in self.extracoes if e.valor is not None)


def ler_release(
    texto: str, company_code: str, metrics: list[str] | None = None
) -> ResultadoRelease:
    """Lê um release inteiro, tentando extrair cada indicador pedido."""
    metrics = metrics or list(SINONIMOS.keys())
    res = ResultadoRelease(company_code=company_code)
    for metric in metrics:
        res.extracoes.append(extrair_metric(texto, metric))
    return res
