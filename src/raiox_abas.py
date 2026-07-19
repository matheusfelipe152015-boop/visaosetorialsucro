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


def _fmt_num_br(v, casas: int = 0) -> str:
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
        # formata colunas numéricas: inteiros BR + percentual no R/L
        formatos = {}
        for col in df.columns:
            cl = str(col).lower()
            if cl in ("r/l",):
                formatos[col] = lambda v: fmt_pct(v)
            elif any(t in cl for t in ["r$", "mm", "limite", "risco", "delta", "notch"]):
                formatos[col] = lambda v: fmt_int_br(v)

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


# ── formatação profissional (inteiros + MM) ──────────────────────────────

def fmt_int_br(v) -> str:
    """Inteiro no padrão brasileiro: 76.135 (sem casas decimais)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    try:
        return f"{float(v):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(v)


def fmt_mm(v) -> str:
    """Valor em reais -> 'R$ 1.234 MM' (inteiro, milhões)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    try:
        return f"R$ {fmt_int_br(float(v) / 1_000_000)} MM"
    except (ValueError, TypeError):
        return "–"


def fmt_pct(v, casas: int = 0) -> str:
    """0.66 -> '66%'."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    try:
        s = f"{float(v) * 100:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return s + "%"
    except (ValueError, TypeError):
        return "–"


# cores por faixa de rating (harmonizadas com a plataforma)
BUCKET_COLORS = {
    "A1 - Baa4": "#14573A",       # verde escuro (melhor)
    "Ba1 - Ba4": "#C6881C",       # âmbar (médio)
    "Ba6 ou pior": "#B4462E",     # vermelho terroso (pior)
    "Não classificado": "#9AA6A0",
}


def aplicar_layout(fig, altura: int = 340, titulo: str | None = None):
    """Layout padrão profissional dos gráficos (limpo, fonte da plataforma)."""
    fig.update_layout(
        template="simple_white",
        height=altura,
        title=titulo,
        title_font={"size": 15, "color": "#18241F"},
        margin={"l": 10, "r": 10, "t": 46 if titulo else 16, "b": 10},
        font={"color": "#18241F", "size": 13},
        legend={"orientation": "h", "y": -0.15},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def fig_risco_disponibilidade_setor(df: pd.DataFrame):
    """Barras empilhadas: risco + disponibilidade por setor (fiel ao original)."""
    import plotly.graph_objects as go
    g = (
        df.groupby("setor_gerencial", as_index=False)
        .agg(risco=("risco", "sum"), disponibilidade=("disponibilidade", "sum"),
             limite=("limite", "sum"))
        .sort_values("limite", ascending=True).tail(12)
    )
    fig = go.Figure()
    fig.add_bar(y=g["setor_gerencial"], x=g["risco"], orientation="h",
                name="Risco", marker_color="#14573A",
                text=[fmt_mm(v) for v in g["risco"]], textposition="inside",
                insidetextanchor="middle")
    fig.add_bar(y=g["setor_gerencial"], x=g["disponibilidade"], orientation="h",
                name="Disponibilidade", marker_color="#CBD8D0",
                text=[fmt_mm(v) for v in g["disponibilidade"]], textposition="inside",
                insidetextanchor="middle")
    fig.update_layout(barmode="stack")
    return aplicar_layout(fig, altura=420, titulo="Risco × Disponibilidade por setor")


def fig_donut(df: pd.DataFrame, valor: str, titulo: str):
    """Donut por faixa de rating (risco ou limite), fiel ao original."""
    import plotly.express as px
    d = (
        df.groupby("bucket_rating", as_index=False)
        .agg(v=(valor, "sum"), grupos=("grupo", "nunique"))
    )
    d = d[d["v"] > 0]
    if d.empty:
        return None
    fig = px.pie(d, names="bucket_rating", values="v", hole=0.62,
                 color="bucket_rating", color_discrete_map=BUCKET_COLORS,
                 custom_data=["grupos"])
    fig.update_traces(
        textinfo="percent",
        hovertemplate=("<b>%{label}</b><br>R$ %{value:,.0f}"
                       "<br>%{customdata[0]} grupos<extra></extra>"),
    )
    return aplicar_layout(fig, altura=330, titulo=titulo)


def fig_por_dimensao(df: pd.DataFrame, coluna: str, titulo: str, top_n: int = 12):
    """Barras horizontais de risco por uma dimensão (analista, officer, diretor...)."""
    import plotly.express as px
    if coluna not in df.columns:
        return None
    d = (
        df.groupby(coluna, as_index=False)["risco"].sum()
        .sort_values("risco", ascending=False).head(top_n)
    )
    d = d[d["risco"] > 0]
    if d.empty:
        return None
    fig = px.bar(d, x="risco", y=coluna, orientation="h",
                 color_discrete_sequence=["#14573A"],
                 text=[fmt_mm(v) for v in d["risco"]])
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis={"categoryorder": "total ascending"},
                      xaxis_title=None, yaxis_title=None)
    return aplicar_layout(fig, altura=max(300, 34 * len(d) + 90), titulo=titulo)


def concentracao_top(df: pd.DataFrame, n: int = 10) -> dict:
    """Concentração: quanto do risco está nos top N grupos."""
    por_grupo = df.groupby("grupo")["risco"].sum().sort_values(ascending=False)
    total = float(por_grupo.sum())
    topo = float(por_grupo.head(n).sum())
    return {"top_n": n, "risco_top": topo, "risco_total": total,
            "pct": (topo / total) if total else 0.0}


# ── Visitas (fiel ao Raio X original) ─────────────────────────────────────
# Regras: "Sem visita" (nunca visitado), "Ba4 ou acima | 12m+" (rating_num <= 5
# e 12+ meses sem visita), "Ba6 ou abaixo | 6m+" (rating_num >= 6 e 6+ meses),
# "Em dia" (o resto).

def _meses_sem_visita(out: pd.DataFrame) -> pd.Series:
    hoje = pd.Timestamp.today().normalize()
    dv = pd.to_datetime(out["data_visita"], errors="coerce", dayfirst=True)
    return (hoje.year - dv.dt.year) * 12 + (hoje.month - dv.dt.month)


def _mascaras_visita(out: pd.DataFrame):
    dv = pd.to_datetime(out["data_visita"], errors="coerce", dayfirst=True)
    meses = _meses_sem_visita(out)
    m_sem = dv.isna()
    m_ba4 = out["rating_num"].notna() & (out["rating_num"] <= 5) & (meses >= 12) & ~m_sem
    m_ba6 = out["rating_num"].notna() & (out["rating_num"] >= 6) & (meses >= 6) & ~m_sem
    m_fora = m_sem | m_ba4 | m_ba6
    return m_sem, m_ba4, m_ba6, ~m_fora, meses


def build_visitas_resumo(df: pd.DataFrame) -> pd.DataFrame:
    """Resumo por categoria de visita: grupos, risco e percentuais."""
    if "rating_num" not in df.columns:
        return pd.DataFrame()
    out = df.copy()
    if "data_visita" not in out.columns:
        out["data_visita"] = pd.NaT
    out["risco"] = pd.to_numeric(out.get("risco", 0), errors="coerce").fillna(0)
    m_sem, m_ba4, m_ba6, m_ok, _ = _mascaras_visita(out)

    total_grupos = out["grupo"].nunique()
    total_risco = out["risco"].sum()

    linhas = []
    for nome, mask in [("Em dia", m_ok), ("Sem visita", m_sem),
                       ("Ba4 ou acima | 12m+", m_ba4), ("Ba6 ou abaixo | 6m+", m_ba6)]:
        grupos = out.loc[mask, "grupo"].nunique()
        risco = out.loc[mask, "risco"].sum()
        linhas.append({
            "Categoria": nome, "Grupos": grupos, "Risco": risco,
            "% Grupos": (grupos / total_grupos) if total_grupos else pd.NA,
            "% Risco": (risco / total_risco) if total_risco else pd.NA,
        })
    return pd.DataFrame(linhas)


def build_visitas_views(df: pd.DataFrame):
    """As 3 tabelas de detalhe: sem visita, Ba4+ 12m+, Ba6- 6m+."""
    if "rating_num" not in df.columns:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    out = df.copy()
    if "data_visita" not in out.columns:
        out["data_visita"] = pd.NaT
    m_sem, m_ba4, m_ba6, _, meses = _mascaras_visita(out)
    out["meses_sem_visita"] = meses

    cols = [c for c in ["id", "grupo", "analista", "rating", "limite", "risco",
                        "data_visita", "meses_sem_visita"] if c in out.columns]
    sem = out[m_sem][cols].sort_values("grupo")
    ba4 = out[m_ba4][cols].sort_values("meses_sem_visita", ascending=False)
    ba6 = out[m_ba6][cols].sort_values("meses_sem_visita", ascending=False)
    return sem, ba4, ba6


# ── Próximos Vencimentos (regra do dia 5 + renovação automática) ──────────

def _eh_renovacao_automatica(serie: pd.Series) -> pd.Series:
    txt = serie.fillna("").astype(str).str.lower()
    return txt.str.contains("eleg") | txt.str.contains("autom") | txt.eq("sim")


def vencimentos_mensais(df: pd.DataFrame, meses_futuros: int = 18) -> pd.DataFrame:
    """Vencimentos por mês, a partir do mês vigente (que só vira no dia 5).

    Devolve: Período, Risco (reais), Grupos, Renovação automática.
    """
    col = "data_venc_limite"
    if col not in df.columns:
        return pd.DataFrame()
    d = df.copy()
    d[col] = pd.to_datetime(d[col], errors="coerce", dayfirst=True)
    d = d[d[col].notna()]
    if d.empty:
        return pd.DataFrame()

    # regra do dia 5: até o dia 4 o "mês vigente" ainda é o anterior
    hoje = pd.Timestamp.today().normalize()
    inicio = (hoje - pd.Timedelta(days=4)).replace(day=1)
    fim = inicio + pd.DateOffset(months=meses_futuros)
    d = d[(d[col] >= inicio) & (d[col] < fim)]
    if d.empty:
        return pd.DataFrame()

    d["_mes"] = d[col].dt.to_period("M")
    if "elegibilidade" in d.columns:
        d["_renov"] = _eh_renovacao_automatica(d["elegibilidade"])
    else:
        d["_renov"] = False

    g = (d.groupby("_mes")
         .agg(Risco=("risco", "sum"), Grupos=("grupo", "nunique"),
              Renovacao=("_renov", "sum"))
         .reset_index())
    meses_pt = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
                7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}
    g["Período"] = g["_mes"].apply(lambda p: f"{meses_pt[p.month]}/{p.year}")
    g = g.sort_values("_mes")
    g["Renovação automática"] = g["Renovacao"].astype(int)
    return g[["Período", "Risco", "Grupos", "Renovação automática"]]
