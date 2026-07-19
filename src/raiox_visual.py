"""Camada visual do Raio X — formatação, cards e gráficos profissionais.

Tudo aqui segue o padrão: valores em R$ MM inteiros (sem casas decimais),
cores harmonizadas com a plataforma (verde cana), gráficos com visual limpo.
As visões replicam as do Raio X original (donuts com total no centro, barras
empilhadas por setor, concentração por bucket), adaptadas ao tema.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── paleta (harmonizada com a plataforma) ─────────────────────────────────
VERDE = "#14573A"
VERDE_ESCURO = "#0E3F2A"
AMBAR = "#C6881C"
TERRACOTA = "#B4462E"
TINTA = "#18241F"
TINTA_SUAVE = "#5C6B63"
FUNDO = "#FAF8F3"
LINHA = "#E6E2D6"

BUCKET_COLORS = {
    "A1 - Baa4": VERDE,
    "Ba1 - Ba4": AMBAR,
    "Ba6 ou pior": TERRACOTA,
    "Não classificado": "#9AA5A0",
}

_LAYOUT_PADRAO = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TINTA, family="sans-serif"),
    margin=dict(l=10, r=10, t=40, b=10),
)


# ── formatação (R$ MM inteiro) ────────────────────────────────────────────

def fmt_mm(v) -> str:
    """Reais -> 'R$ 1.234 MM' (inteiro, padrão brasileiro)."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    try:
        mm = float(v) / 1_000_000
        s = f"{mm:,.0f}".replace(",", ".")
        return f"R$ {s} MM"
    except (ValueError, TypeError):
        return str(v)


def fmt_int(v) -> str:
    """Número inteiro no padrão brasileiro: 1.234."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    try:
        return f"{float(v):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(v)


def fmt_pct(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    try:
        return f"{float(v) * 100:,.0f}%".replace(",", ".")
    except (ValueError, TypeError):
        return str(v)


# ── cards KPI (HTML profissional, sem truncar) ────────────────────────────

def kpi_html(itens: list[tuple[str, str, str]]) -> str:
    """Linha de cards KPI. itens = [(rotulo, valor, complemento), ...]."""
    cards = []
    for rotulo, valor, sub in itens:
        cards.append(
            f'<div style="flex:1;min-width:150px;background:#fff;'
            f'border:1px solid {LINHA};border-radius:12px;padding:14px 16px;">'
            f'<div style="font-size:11px;letter-spacing:.08em;text-transform:uppercase;'
            f'color:{TINTA_SUAVE};margin-bottom:6px">{rotulo}</div>'
            f'<div style="font-size:24px;font-weight:800;color:{TINTA};'
            f'line-height:1.1">{valor}</div>'
            f'<div style="font-size:12px;color:{TINTA_SUAVE};margin-top:4px">{sub}</div>'
            f"</div>"
        )
    return ('<div style="display:flex;gap:12px;flex-wrap:wrap;margin:4px 0 18px">'
            + "".join(cards) + "</div>")


def secao(titulo: str, sub: str = "") -> str:
    """Cabeçalho de seção estilizado."""
    linha_sub = (f'<div style="font-size:13px;color:{TINTA_SUAVE};margin-top:2px">{sub}</div>'
                 if sub else "")
    return (f'<div style="margin:22px 0 10px">'
            f'<div style="font-size:17px;font-weight:800;color:{TINTA}">{titulo}</div>'
            f"{linha_sub}"
            f'<div style="height:2px;background:{VERDE};width:44px;margin-top:6px;'
            f'border-radius:2px"></div></div>')


# ── gráficos (as visões do Raio X original, no tema da plataforma) ────────

def donut_por_bucket(df: pd.DataFrame, valor: str, titulo: str) -> go.Figure | None:
    """Donut de risco/limite por faixa de rating, com o total no centro."""
    if "bucket_rating" not in df.columns or valor not in df.columns:
        return None
    g = (df.groupby("bucket_rating", as_index=False)
         .agg(v=(valor, "sum"), grupos=("grupo", "nunique")))
    ordem = ["A1 - Baa4", "Ba1 - Ba4", "Ba6 ou pior", "Não classificado"]
    g["bucket_rating"] = pd.Categorical(g["bucket_rating"], categories=ordem, ordered=True)
    g = g.sort_values("bucket_rating")
    g = g[g["v"] > 0]
    if g.empty:
        return None
    total = g["v"].sum()
    fig = px.pie(
        g, names="bucket_rating", values="v", hole=0.62,
        color="bucket_rating", color_discrete_map=BUCKET_COLORS,
        custom_data=["grupos"],
    )
    fig.update_traces(
        sort=False, textposition="inside", texttemplate="%{percent:.0%}",
        textfont=dict(color="#ffffff", size=13),
        marker=dict(line=dict(color="#ffffff", width=2)),
        hovertemplate="<b>%{label}</b><br>" + titulo +
                      ": %{value:,.0f}<br>%{percent} · %{customdata[0]} grupos<extra></extra>",
    )
    fig.update_layout(
        **_LAYOUT_PADRAO, height=330, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.14, x=0.5,
                    xanchor="center", title=""),
        annotations=[dict(
            text=f"<b>{fmt_mm(total)}</b><br><span style='font-size:11px;"
                 f"color:{TINTA_SUAVE}'>{titulo}</span>",
            x=0.5, y=0.5, showarrow=False, font=dict(size=14, color=TINTA),
        )],
    )
    return fig


def barras_setor_risco_disp(df: pd.DataFrame) -> go.Figure | None:
    """Barras empilhadas horizontais: risco + disponibilidade por setor."""
    if "setor_gerencial" not in df.columns:
        return None
    g = (df.groupby("setor_gerencial", as_index=False)
         .agg(risco=("risco", "sum"), disponibilidade=("disponibilidade", "sum"),
              limite=("limite", "sum"))
         .sort_values("limite", ascending=True))
    if g.empty:
        return None
    fig = go.Figure()
    fig.add_bar(y=g["setor_gerencial"], x=g["risco"], orientation="h",
                name="Risco", marker_color=VERDE,
                text=[fmt_mm(v) for v in g["risco"]], textposition="inside",
                insidetextfont=dict(color="#fff", size=11),
                hovertemplate="<b>%{y}</b><br>Risco: R$ %{x:,.0f}<extra></extra>")
    fig.add_bar(y=g["setor_gerencial"], x=g["disponibilidade"], orientation="h",
                name="Disponível", marker_color="#CFDCD4",
                text=[fmt_mm(v) for v in g["disponibilidade"]], textposition="inside",
                insidetextfont=dict(color=TINTA, size=11),
                hovertemplate="<b>%{y}</b><br>Disponível: R$ %{x:,.0f}<extra></extra>")
    fig.update_layout(
        **_LAYOUT_PADRAO, barmode="stack",
        height=max(340, 44 * len(g) + 90),
        xaxis_title="", yaxis_title="",
        xaxis=dict(showticklabels=False, showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


def top_concentracao(df: pd.DataFrame, n: int = 10) -> go.Figure | None:
    """Top N grupos por risco, colorido pela faixa de rating."""
    if df.empty or "risco" not in df.columns:
        return None
    top = df.sort_values("risco", ascending=False).head(n).copy()
    if top.empty:
        return None
    top = top.sort_values("risco", ascending=True)
    fig = px.bar(
        top, x="risco", y="grupo", orientation="h",
        color="bucket_rating" if "bucket_rating" in top.columns else None,
        color_discrete_map=BUCKET_COLORS,
        text=top["risco"].map(fmt_mm),
    )
    fig.update_traces(textposition="outside", cliponaxis=False,
                      hovertemplate="<b>%{y}</b><br>Risco: R$ %{x:,.0f}<extra></extra>")
    fig.update_layout(
        **_LAYOUT_PADRAO, height=max(340, 34 * len(top) + 80),
        xaxis=dict(showticklabels=False, showgrid=False), xaxis_title="", yaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=""),
    )
    return fig


def barras_por_dimensao(df: pd.DataFrame, dim: str, titulo_eixo: str,
                        n: int = 12) -> go.Figure | None:
    """Risco por uma dimensão qualquer (analista, officer, diretor...)."""
    if dim not in df.columns:
        return None
    g = (df.groupby(dim, as_index=False).agg(risco=("risco", "sum"))
         .sort_values("risco", ascending=False).head(n).sort_values("risco", ascending=True))
    g = g[g["risco"] > 0]
    if g.empty:
        return None
    fig = px.bar(g, x="risco", y=dim, orientation="h",
                 text=g["risco"].map(fmt_mm), color_discrete_sequence=[VERDE])
    fig.update_traces(textposition="outside", cliponaxis=False,
                      hovertemplate="<b>%{y}</b><br>Risco: R$ %{x:,.0f}<extra></extra>")
    fig.update_layout(
        **_LAYOUT_PADRAO, height=max(300, 34 * len(g) + 70),
        xaxis=dict(showticklabels=False, showgrid=False),
        xaxis_title="", yaxis_title=titulo_eixo,
    )
    return fig


# ── filtros ───────────────────────────────────────────────────────────────

_DIMENSOES_FILTRO = [
    ("analista", "Analista"),
    ("setor_gerencial", "Setor gerencial"),
    ("bucket_rating", "Faixa de rating"),
    ("officer", "Officer"),
    ("diretor_comercial", "Diretor comercial"),
]


def opcoes_filtro(df: pd.DataFrame) -> list[tuple[str, str, list[str]]]:
    """Dimensões disponíveis na base + suas opções (só as com 2+ valores)."""
    out = []
    for col, rotulo in _DIMENSOES_FILTRO:
        if col in df.columns:
            vals = sorted(v for v in df[col].dropna().astype(str).str.strip().unique()
                          if v and v.lower() not in ("nan", "none"))
            if len(vals) >= 2:
                out.append((col, rotulo, vals))
    return out


def aplicar_filtros(df: pd.DataFrame, escolhas: dict[str, list[str]]) -> pd.DataFrame:
    """Filtra a base pelas escolhas (lista vazia = sem filtro naquela dimensão)."""
    out = df
    for col, selecionados in escolhas.items():
        if selecionados and col in out.columns:
            out = out[out[col].astype(str).str.strip().isin(selecionados)]
    return out
