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
                textangle=0, insidetextfont=dict(color="#fff", size=11),
                hovertemplate="<b>%{y}</b><br>Risco: R$ %{x:,.0f}<extra></extra>")
    fig.add_bar(y=g["setor_gerencial"], x=g["disponibilidade"], orientation="h",
                name="Disponível", marker_color="#CFDCD4",
                text=[fmt_mm(v) for v in g["disponibilidade"]], textposition="inside",
                textangle=0, insidetextfont=dict(color=TINTA, size=11),
                hovertemplate="<b>%{y}</b><br>Disponível: R$ %{x:,.0f}<extra></extra>")
    fig.update_layout(
        **_LAYOUT_PADRAO, barmode="stack", uniformtext_minsize=9,
        uniformtext_mode="hide",
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
    fig.update_traces(textposition="outside", cliponaxis=False, textangle=0,
                      hovertemplate="<b>%{y}</b><br>Risco: R$ %{x:,.0f}<extra></extra>")
    fig.update_layout(
        **_LAYOUT_PADRAO, height=max(340, 34 * len(top) + 80),
        xaxis=dict(showticklabels=False, showgrid=False,
                   range=[0, float(top["risco"].max()) * 1.25]),
        xaxis_title="", yaxis_title="",
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
    fig.update_traces(textposition="outside", cliponaxis=False, textangle=0,
                      hovertemplate="<b>%{y}</b><br>Risco: R$ %{x:,.0f}<extra></extra>")
    fig.update_layout(
        **_LAYOUT_PADRAO, height=max(300, 34 * len(g) + 70),
        xaxis=dict(showticklabels=False, showgrid=False,
                   range=[0, float(g["risco"].max()) * 1.25]),
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


# ── donut de cobertura de visitas (fiel ao original, no tema) ─────────────

CORES_COBERTURA = {
    "Em dia": VERDE,
    "Sem visita": "#3C4A44",
    "Ba4 ou acima | 12m+": AMBAR,
    "Ba6 ou abaixo | 6m+": TERRACOTA,
}
ORDEM_COBERTURA = ["Em dia", "Sem visita", "Ba4 ou acima | 12m+", "Ba6 ou abaixo | 6m+"]


def donut_cobertura(resumo: pd.DataFrame, col_abs: str, col_pct: str,
                    titulo: str) -> go.Figure | None:
    """Rosca de cobertura de visitas com o % 'Em dia' no centro."""
    if resumo.empty or col_abs not in resumo.columns:
        return None
    idx = resumo.set_index("Categoria")
    labels = [c for c in ORDEM_COBERTURA if c in idx.index and
              pd.notna(idx.loc[c, col_abs]) and idx.loc[c, col_abs] > 0]
    if not labels:
        return None
    vals = [float(idx.loc[c, col_abs]) for c in labels]
    cores = [CORES_COBERTURA[c] for c in labels]
    cob = idx.loc["Em dia", col_pct] if "Em dia" in idx.index else None
    cob_txt = "–" if (cob is None or pd.isna(cob)) else f"{cob:.0%}".replace(".", ",")

    fig = go.Figure(go.Pie(
        labels=labels, values=vals, hole=0.64, sort=False, direction="clockwise",
        marker=dict(colors=cores, line=dict(color="#ffffff", width=2)),
        texttemplate="%{percent:.0%}", textposition="inside",
        insidetextfont=dict(color="#ffffff", size=12),
        hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT_PADRAO, title=titulo, height=340,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, x=0.5,
                    xanchor="center", title=""),
        annotations=[dict(
            text=f"Em dia<br><b style='font-size:18px'>{cob_txt}</b>",
            x=0.5, y=0.5, font=dict(size=13, color=TINTA), showarrow=False,
        )],
    )
    return fig


# ── gráfico de vencimentos: risco + grupos + renovação automática ─────────

def grafico_vencimentos(venc: pd.DataFrame) -> go.Figure | None:
    """3 barras por mês: risco (eixo 1), grupos e renovação automática (eixo 2)."""
    if venc is None or venc.empty:
        return None
    fig = go.Figure()
    fig.add_bar(x=venc["Período"], y=venc["Risco"], name="Risco vencendo",
                offsetgroup="risco", marker_color=VERDE,
                text=[fmt_mm(v) for v in venc["Risco"]],
                textposition="outside", textangle=0, cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Risco: R$ %{y:,.0f}<extra></extra>")
    fig.add_bar(x=venc["Período"], y=venc["Grupos"], name="Grupos", yaxis="y2",
                offsetgroup="grupos", marker_color=AMBAR, text=venc["Grupos"],
                textposition="outside", textangle=0, cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Grupos: %{y}<extra></extra>")
    fig.add_bar(x=venc["Período"], y=venc["Renovação automática"],
                name="Renovação automática", yaxis="y2", offsetgroup="renov",
                marker_color="#8FB3A2", text=venc["Renovação automática"],
                textposition="outside", textangle=0, cliponaxis=False,
                hovertemplate="<b>%{x}</b><br>Renov. automática: %{y}<extra></extra>")
    fig.update_layout(**_LAYOUT_PADRAO)
    fig.update_layout(
        barmode="group", height=420,
        yaxis=dict(title="Risco (R$)", showgrid=False, showticklabels=False),
        yaxis2=dict(title="Grupos", overlaying="y", side="right",
                    showgrid=False, showticklabels=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        margin=dict(l=10, r=10, t=60, b=10),
    )
    return fig


# ── novas visões (propostas a partir da análise da base) ──────────────────

def heatmap_setor_faixa(df: pd.DataFrame) -> go.Figure | None:
    """Matriz setor gerencial × faixa de rating (risco em MM)."""
    if not {"setor_gerencial", "bucket_rating", "risco"}.issubset(df.columns):
        return None
    piv = df.pivot_table(index="setor_gerencial", columns="bucket_rating",
                         values="risco", aggfunc="sum", fill_value=0)
    ordem = [c for c in ["A1 - Baa4", "Ba1 - Ba4", "Ba6 ou pior"] if c in piv.columns]
    if not ordem or piv.empty:
        return None
    piv = piv[ordem]
    piv = piv.loc[piv.sum(axis=1).sort_values(ascending=True).index]
    texto = [[fmt_mm(v) for v in linha] for linha in piv.values]
    fig = go.Figure(go.Heatmap(
        z=piv.values, x=list(piv.columns), y=list(piv.index),
        text=texto, texttemplate="%{text}", textfont=dict(size=11),
        colorscale=[[0, "#F2F0E9"], [1, VERDE]], showscale=False,
        hovertemplate="<b>%{y}</b> · %{x}<br>Risco: R$ %{z:,.0f}<extra></extra>",
    ))
    fig.update_layout(**_LAYOUT_PADRAO, height=max(320, 40 * len(piv) + 90))
    return fig


def pareto_concentracao(df: pd.DataFrame) -> go.Figure | None:
    """Concentração acumulada: % do risco total nos N maiores grupos."""
    if "risco" not in df.columns or df.empty:
        return None
    g = (df.groupby("grupo")["risco"].sum()
         .sort_values(ascending=False).reset_index())
    total = g["risco"].sum()
    if total <= 0:
        return None
    g["acum"] = g["risco"].cumsum() / total
    g["n"] = range(1, len(g) + 1)
    fig = go.Figure(go.Scatter(
        x=g["n"], y=g["acum"], mode="lines", line=dict(color=VERDE, width=3),
        fill="tozeroy", fillcolor="rgba(20,87,58,0.08)",
        hovertemplate="Top %{x} grupos<br>%{y:.0%} do risco<extra></extra>",
    ))
    for marco in (10, 20, 50):
        if marco <= len(g):
            pct = g.loc[g["n"] == marco, "acum"].iloc[0]
            fig.add_annotation(x=marco, y=pct, text=f"Top {marco}: {pct:.0%}".replace(".", ","),
                               showarrow=True, arrowhead=0, ax=0, ay=-28,
                               font=dict(size=11, color=TINTA))
    fig.update_layout(
        **_LAYOUT_PADRAO, height=330,
        xaxis=dict(title="Nº de grupos (do maior para o menor)", showgrid=False),
        yaxis=dict(title="% do risco acumulado", tickformat=".0%", showgrid=True,
                   gridcolor=LINHA),
    )
    return fig


def histograma_utilizacao(df: pd.DataFrame) -> go.Figure | None:
    """Distribuição da utilização (risco / limite) dos grupos."""
    if not {"risco", "limite"}.issubset(df.columns):
        return None
    d = df[(df["limite"] > 0)].copy()
    if d.empty:
        return None
    d["uso"] = (d["risco"] / d["limite"]).clip(0, 1.5)
    fig = px.histogram(d, x="uso", nbins=20, color_discrete_sequence=[VERDE])
    fig.update_traces(hovertemplate="Utilização: %{x:.0%}<br>Grupos: %{y}<extra></extra>")
    fig.update_layout(
        **_LAYOUT_PADRAO, height=320, bargap=0.06,
        xaxis=dict(title="Utilização do limite (risco ÷ limite)", tickformat=".0%"),
        yaxis=dict(title="Nº de grupos", showgrid=True, gridcolor=LINHA),
    )
    return fig
