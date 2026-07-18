"""Funções de tabela e gráfico para as abas do Raio X.

Reproduz a lógica do app original (Tabelas de Rating, Movimentações, Próximos
Vencimentos...), adaptada para os dados normalizados da plataforma. Cada função
devolve um DataFrame pronto para exibir, com as linhas de total/delta.
"""

from __future__ import annotations

import pandas as pd

_COLS_BASE = ["grupo", "rating", "limite", "risco", "rl"]
_NOMES = ["Grupo", "Rating", "Limite (R$ mm)", "Risco (R$ mm)", "R/L"]


def _mm(v) -> float:
    """Converte para milhões (a base guarda em reais)."""
    try:
        return float(v) / 1_000_000
    except (ValueError, TypeError):
        return 0.0


def _linha_total(nome, limite, risco, rating="-"):
    return {
        "Grupo": nome, "Rating": rating,
        "Limite (R$ mm)": _mm(limite), "Risco (R$ mm)": _mm(risco),
        "R/L": (risco / limite) if limite else pd.NA,
    }


def table_top_bucket(df: pd.DataFrame, bucket: str, top_n: int = 10) -> pd.DataFrame:
    """Top N grupos por limite dentro de uma faixa de rating, com totais e delta."""
    if "bucket_rating" not in df.columns:
        return pd.DataFrame()
    d = df[df["bucket_rating"] == bucket].copy().sort_values("limite", ascending=False)
    if d.empty:
        return pd.DataFrame()
    top = d.head(top_n)[_COLS_BASE].copy()
    top.columns = _NOMES
    top["Limite (R$ mm)"] = top["Limite (R$ mm)"].apply(_mm)
    top["Risco (R$ mm)"] = top["Risco (R$ mm)"].apply(_mm)

    lim_exib = d.head(top_n)["limite"].sum()
    ris_exib = d.head(top_n)["risco"].sum()
    lim_cart = d["limite"].sum()
    ris_cart = d["risco"].sum()

    extras = pd.DataFrame([
        _linha_total("Total exibido", lim_exib, ris_exib),
        _linha_total(f"Total carteira {bucket}", lim_cart, ris_cart),
        _linha_total("Delta", lim_cart - lim_exib, ris_cart - ris_exib),
    ])
    return pd.concat([top, extras], ignore_index=True)


def table_b2_ou_pior(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Top N por risco entre os grupos com rating B2 ou pior (rating_num >= 8)."""
    if "rating_num" not in df.columns:
        return pd.DataFrame()
    d = df[df["rating_num"] >= 8].copy().sort_values("risco", ascending=False)
    if d.empty:
        return pd.DataFrame()
    top = d.head(top_n)[_COLS_BASE].copy()
    top.columns = _NOMES
    top["Limite (R$ mm)"] = top["Limite (R$ mm)"].apply(_mm)
    top["Risco (R$ mm)"] = top["Risco (R$ mm)"].apply(_mm)

    lim_exib = d.head(top_n)["limite"].sum()
    ris_exib = d.head(top_n)["risco"].sum()
    lim_cart = d["limite"].sum()
    ris_cart = d["risco"].sum()

    extras = pd.DataFrame([
        _linha_total("Total exibido", lim_exib, ris_exib),
        _linha_total("Total carteira B2 ou pior", lim_cart, ris_cart),
        _linha_total("Delta", lim_cart - lim_exib, ris_cart - ris_exib),
    ])
    return pd.concat([top, extras], ignore_index=True)


def movement_available(df: pd.DataFrame) -> bool:
    """A base tem as colunas de comparação com o mês anterior (M-1)?"""
    return {"delta_limite", "delta_risco", "delta_rating"}.issubset(df.columns)


def table_movement(df: pd.DataFrame, metric: str, direction: str,
                   top_n: int = 10) -> pd.DataFrame:
    """Top N maiores variações de limite ou risco (subida ou descida)."""
    delta_col = "delta_limite" if metric == "limite" else "delta_risco"
    atual_col = "limite" if metric == "limite" else "risco"
    rotulo = "Limite" if metric == "limite" else "Risco"
    d = df.copy()
    if direction == "up":
        d = d[d[delta_col] > 0].sort_values(delta_col, ascending=False)
    else:
        d = d[d[delta_col] < 0].sort_values(delta_col, ascending=True)
    if d.empty:
        return pd.DataFrame()

    top = d.head(top_n)[["grupo", "rating", delta_col, atual_col]].copy()
    top.columns = ["Grupo", "Rating", f"Delta {rotulo} (R$ mm)", f"{rotulo} (R$ mm)"]
    top[f"Delta {rotulo} (R$ mm)"] = top[f"Delta {rotulo} (R$ mm)"].apply(_mm)
    top[f"{rotulo} (R$ mm)"] = top[f"{rotulo} (R$ mm)"].apply(_mm)
    return top


def table_rating_movement(df: pd.DataFrame, direction: str,
                          top_n: int = 10) -> pd.DataFrame:
    """Upgrades ou downgrades de rating no mês (delta_rating)."""
    d = df.copy()
    if direction == "upgrade":
        d = d[d["delta_rating"] > 0].sort_values("delta_rating", ascending=False)
    else:
        d = d[d["delta_rating"] < 0].sort_values("delta_rating", ascending=True)
    if d.empty:
        return pd.DataFrame()
    top = d.head(top_n)[["grupo", "rating", "delta_rating", "limite", "risco"]].copy()
    top.columns = ["Grupo", "Rating", "Delta notches", "Limite (R$ mm)", "Risco (R$ mm)"]
    top["Limite (R$ mm)"] = top["Limite (R$ mm)"].apply(_mm)
    top["Risco (R$ mm)"] = top["Risco (R$ mm)"].apply(_mm)
    return top


def tabela_vencimentos(df: pd.DataFrame) -> pd.DataFrame:
    """Grupos por ano/mês de vencimento de limite (se a base tiver a data)."""
    col = "data_venc_limite"
    if col not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    d[col] = pd.to_datetime(d[col], errors="coerce", dayfirst=True)
    d = d[d[col].notna()]
    if d.empty:
        return pd.DataFrame()
    d["Ano"] = d[col].dt.year
    d["Mês"] = d[col].dt.month
    agrupado = (
        d.groupby(["Ano", "Mês"])
        .agg(Grupos=("grupo", "nunique"), Risco=("risco", "sum"))
        .reset_index()
    )
    agrupado["Risco (R$ mm)"] = agrupado["Risco"].apply(_mm)
    return agrupado[["Ano", "Mês", "Grupos", "Risco (R$ mm)"]]


# ── Qualidade / Pendências ────────────────────────────────────────────────

def _vazio(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower().isin(
        ["", "nan", "none", "-", "não informado", "nao informado", "nr", "null"]
    )


def build_qualidade(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Monta o resumo de pendências da base + os detalhes de cada uma."""
    out = df.copy()
    for c in ["data_visita", "data_venc_rating", "data_venc_limite"]:
        if c in out.columns:
            out[c] = pd.to_datetime(out[c], errors="coerce", dayfirst=True)

    checks = []
    if "bucket_rating" in out.columns:
        checks.append(("Rating não mapeado", out["bucket_rating"].eq("Não classificado")))
    if "setor_gerencial" in out.columns:
        checks.append(("Setor gerencial não informado", _vazio(out["setor_gerencial"])))
    if "data_visita" in out.columns:
        checks.append(("Sem data de visita", out["data_visita"].isna()))
    if {"risco", "limite"}.issubset(out.columns):
        checks.append(("Risco maior que limite", out["risco"] > out["limite"]))
        checks.append(("Limite zerado com risco", (out["limite"] <= 0) & (out["risco"] > 0)))
    if "analista" in out.columns:
        checks.append(("Cliente sem analista", _vazio(out["analista"])))
    if "data_venc_rating" in out.columns:
        checks.append(("Sem vencimento de rating", out["data_venc_rating"].isna()))
    if "data_venc_limite" in out.columns:
        checks.append(("Sem vencimento de limite", out["data_venc_limite"].isna()))

    disp = [c for c in ["id", "grupo", "analista", "setor_gerencial", "rating",
                        "limite", "risco", "data_visita"] if c in out.columns]

    linhas, detalhes = [], {}
    for nome, mask in checks:
        sub = out[mask]
        qtd = int(sub["grupo"].nunique()) if "grupo" in sub.columns else int(len(sub))
        risco = float(sub["risco"].sum()) if "risco" in sub.columns else 0.0
        linhas.append({"Pendência": nome, "Qtd": qtd, "Risco (R$ mm)": _mm(risco)})
        detalhes[nome] = sub[disp].copy()
    return pd.DataFrame(linhas), detalhes


# ── Clientes por analista ─────────────────────────────────────────────────

def clientes_por_analista(df: pd.DataFrame) -> pd.DataFrame:
    """Resumo por analista: nº de clientes, limite e risco."""
    if "analista" not in df.columns:
        return pd.DataFrame()
    resumo = (
        df.groupby("analista", as_index=False)
        .agg(Clientes=("grupo", "nunique"), Limite=("limite", "sum"), Risco=("risco", "sum"))
        .sort_values("Risco", ascending=False)
    )
    resumo["Limite (R$ mm)"] = resumo["Limite"].apply(_mm)
    resumo["Risco (R$ mm)"] = resumo["Risco"].apply(_mm)
    return resumo[["analista", "Clientes", "Limite (R$ mm)", "Risco (R$ mm)"]].rename(
        columns={"analista": "Analista"})


# ── Visitas ───────────────────────────────────────────────────────────────

def cobertura_visitas(df: pd.DataFrame) -> pd.DataFrame:
    """Por analista: quantos clientes têm data de visita e quantos não têm."""
    if "analista" not in df.columns or "data_visita" not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    d["data_visita"] = pd.to_datetime(d["data_visita"], errors="coerce", dayfirst=True)
    d["tem_visita"] = d["data_visita"].notna()
    resumo = (
        d.groupby("analista")
        .agg(Clientes=("grupo", "nunique"),
             Com_visita=("tem_visita", "sum"),
             Risco=("risco", "sum"))
        .reset_index()
    )
    resumo["Sem visita"] = resumo["Clientes"] - resumo["Com_visita"]
    resumo["Risco (R$ mm)"] = resumo["Risco"].apply(_mm)
    return resumo.rename(columns={"analista": "Analista", "Com_visita": "Com visita"})[
        ["Analista", "Clientes", "Com visita", "Sem visita", "Risco (R$ mm)"]]


# ── estilo das tabelas (deixa bonito) ─────────────────────────────────────

# cores harmonizadas com a plataforma (verde cana)
_VERDE = "#14573A"
_VERDE_CLARO = "#EAF2ED"
_AMBAR = "#C6881C"
_TINTA = "#18241F"
_LINHA_TOTAL = "#F3EFE4"

_ROTULOS_TOTAL = {"total exibido", "delta", "total carteira"}


def _e_linha_total(nome: str) -> bool:
    n = str(nome).strip().lower()
    return any(n.startswith(r) for r in _ROTULOS_TOTAL)


def _fmt_num_br(v, casas: int = 1) -> str:
    """Número no padrão brasileiro: 1.234,5 (sem notação científica)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    try:
        s = f"{float(v):,.{casas}f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(v)


def estilizar(df: pd.DataFrame):
    """Devolve um Styler bonito: números BR, linhas de total destacadas, cores.

    Use com st.dataframe(estilizar(tabela), ...). Se algo falhar, devolve o df cru.
    """
    if df is None or df.empty:
        return df
    try:
        # formata colunas numéricas no padrão brasileiro
        formatos = {}
        for col in df.columns:
            cl = str(col).lower()
            if any(t in cl for t in ["r$", "mm", "limite", "risco", "delta", "%", "notch"]):
                casas = 2 if "%" in cl else 1
                formatos[col] = lambda v, c=casas: _fmt_num_br(v, c)

        sty = df.style.format(formatos, na_rep="–")

        # destaca as linhas de total/delta (primeira coluna costuma ser "Grupo")
        primeira = df.columns[0]

        def _destacar(row):
            if _e_linha_total(row.get(primeira, "")):
                return [f"background-color:{_LINHA_TOTAL}; font-weight:700; "
                        f"color:{_VERDE}"] * len(row)
            return [""] * len(row)

        sty = sty.apply(_destacar, axis=1)

        # cabeçalho verde
        sty = sty.set_table_styles([
            {"selector": "th",
             "props": [("background-color", _VERDE), ("color", "white"),
                       ("font-weight", "600"), ("text-align", "left"),
                       ("padding", "8px 10px")]},
            {"selector": "td", "props": [("padding", "7px 10px")]},
        ])
        return sty
    except Exception:  # noqa: BLE001 — se estilizar falhar, mostra a tabela crua
        return df
