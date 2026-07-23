"""Cruza os nomes dos clientes da carteira (de-para) com as manchetes do radar.

A ideia: toda notícia que cita um grupo da carteira ganha a etiqueta do cliente,
para o analista ver o que saiu na imprensa sobre quem ele acompanha.

O casamento é por nome, então é aproximado por natureza: nomes de empresa variam
muito na imprensa ("Usina Cocal" vira "Cocal"; "São Martinho S.A." vira "São
Martinho"). Para reduzir ruído, o texto é normalizado (sem acento, maiúsculas),
os sufixos societários são removidos e a busca exige palavra inteira — assim
"ADM" não casa dentro de "administração". Ainda assim pode haver falso positivo
em nomes curtos ou genéricos; a lista PARADAS existe para esses casos.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd
from sqlalchemy import text

from src.persistence.db import get_engine

# sufixos societários que não ajudam a identificar o grupo
_SUFIXOS = {
    "LTDA", "SA", "S A", "ME", "EPP", "EIRELI", "MEI", "SOCIEDADE", "ANONIMA",
    "ANONIMA FECHADA", "CIA", "COMPANHIA", "PARTICIPACOES", "HOLDING",
}
# palavras que iniciam muitos nomes e sozinhas não identificam ninguém
_PREFIXOS_GENERICOS = {
    "USINA", "USINAS", "GRUPO", "DESTILARIA", "AGROPECUARIA", "AGROINDUSTRIAL",
    "AGRICOLA", "COMPANHIA", "CIA", "INDUSTRIA", "INDUSTRIAL", "COOPERATIVA",
}
# nomes que, sozinhos, dariam casamento em qualquer notícia do setor
PARADAS = {
    "AGRO", "USINA", "GRUPO", "BRASIL", "AGRICOLA", "ALIMENTOS", "ACUCAR",
    "ETANOL", "CANA", "BIOENERGIA", "ENERGIA", "AGROPECUARIA", "RURAL",
    "PRODUTOR", "COOPERATIVA", "INDUSTRIA", "COMERCIO", "TRADING", "SUCROENERGETICO",
}
_MIN_CARACTERES = 3


def normalizar(texto: str) -> str:
    """Sem acento, maiúsculas, só letras e números."""
    if not texto:
        return ""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", str(texto))
        if not unicodedata.combining(c)
    )
    limpo = re.sub(r"[^A-Za-z0-9]+", " ", sem_acento).upper()
    return re.sub(r"\s+", " ", limpo).strip()


def variantes_do_nome(nome: str) -> list[str]:
    """Formas pelas quais o grupo pode aparecer numa manchete."""
    base = normalizar(nome)
    if not base:
        return []
    tokens = base.split()
    # tira sufixos societários do fim
    while tokens and tokens[-1] in _SUFIXOS:
        tokens.pop()
    if not tokens:
        return []

    saida = []
    completo = " ".join(tokens)
    saida.append(completo)
    # "USINA COCAL" também aparece como "COCAL"
    if len(tokens) > 1 and tokens[0] in _PREFIXOS_GENERICOS:
        saida.append(" ".join(tokens[1:]))

    validas = []
    for v in saida:
        if len(v) < _MIN_CARACTERES or v in PARADAS:
            continue
        if v not in validas:
            validas.append(v)
    return validas


def clientes_da_carteira() -> pd.DataFrame:
    """Clientes ativos do de-para: id, grupo e as variantes de nome."""
    with get_engine(readonly=True).connect() as conn:
        df = pd.read_sql_query(
            text("SELECT id_cliente, grupo FROM depara WHERE ativo = 1"), conn)
    if df.empty:
        return pd.DataFrame(columns=["id_cliente", "grupo", "variantes"])
    df["variantes"] = df["grupo"].apply(variantes_do_nome)
    return df[df["variantes"].str.len() > 0].reset_index(drop=True)


def casar_carteira(articles: pd.DataFrame,
                   clientes: pd.DataFrame | None = None) -> pd.DataFrame:
    """Devolve os pares (article_id, id_cliente, grupo) encontrados nos títulos.

    Procura o nome do cliente no título e no resumo, exigindo palavra inteira.
    """
    vazio = pd.DataFrame(columns=["article_id", "id_cliente", "grupo"])
    if articles is None or articles.empty:
        return vazio
    if clientes is None:
        clientes = clientes_da_carteira()
    if clientes.empty:
        return vazio

    # um padrão por variante, compilado uma vez só
    padroes: list[tuple[re.Pattern, str, str]] = []
    for _, c in clientes.iterrows():
        for v in c["variantes"]:
            padroes.append((re.compile(rf"\b{re.escape(v)}\b"),
                            str(c["id_cliente"]), str(c["grupo"])))

    achados = []
    for _, a in articles.iterrows():
        texto = normalizar(f"{a.get('titulo', '')} {a.get('resumo', '') or ''}")
        if not texto:
            continue
        vistos = set()
        for padrao, id_cliente, grupo in padroes:
            if id_cliente in vistos:
                continue
            if padrao.search(texto):
                achados.append({"article_id": a["id"], "id_cliente": id_cliente,
                                "grupo": grupo})
                vistos.add(id_cliente)
    return pd.DataFrame(achados) if achados else vazio
