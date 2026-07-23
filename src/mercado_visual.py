"""Gráficos da aba Mercado — lê as tabelas do sugar-intel e monta as visões.

Todas as funções devolvem uma figura Plotly (ou None se não houver dado), no
tema da plataforma. A página empilha todas de uma vez, sem selectbox.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

from src.persistence.db import get_engine

VERDE = "#14573A"
AMBAR = "#C6881C"
TERRACOTA = "#B4462E"
TINTA = "#18241F"
TINTA_SUAVE = "#5C6B63"
LINHA = "#E6E2D6"

_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TINTA, family="sans-serif"),
    margin=dict(l=10, r=10, t=30, b=10),
)


def _df(sql: str) -> pd.DataFrame:
    with get_engine(readonly=True).connect() as conn:
        return pd.read_sql_query(text(sql), conn)


# ── CFTC: posição líquida dos fundos ──────────────────────────────────────
def fig_cftc() -> go.Figure | None:
    d = _df("SELECT data_ref, esp_net, com_net FROM cftc_sugar ORDER BY data_ref")
    if d.empty:
        return None
    d["data_ref"] = pd.to_datetime(d["data_ref"])
    fig = go.Figure()
    fig.add_bar(x=d["data_ref"], y=d["esp_net"], name="Especuladores (net)",
                marker_color=VERDE)
    fig.add_trace(go.Scatter(x=d["data_ref"], y=d["com_net"], name="Comerciais (net)",
                             mode="lines", line=dict(color=TERRACOTA, width=1.5)))
    fig.add_hline(y=0, line_color=TINTA_SUAVE, line_width=1)
    fig.update_layout(**_LAYOUT, height=340,
                      legend=dict(orientation="h", y=1.02, x=0),
                      yaxis_title="Contratos líquidos", xaxis_title="")
    return fig


# ── Curva a termo NY11 ────────────────────────────────────────────────────
def fig_curva_ny11() -> go.Figure | None:
    d = _df("SELECT vencimento, mes_nome, ano_venc, close_clb, data_ref "
            "FROM ny11_curva WHERE close_clb IS NOT NULL")
    if d.empty:
        return None
    d = d.sort_values(["ano_venc", "vencimento"])
    d["rotulo"] = d["mes_nome"].fillna("") + "/" + d["ano_venc"].astype("Int64").astype(str)
    fig = px.line(d, x="rotulo", y="close_clb", markers=True,
                  color_discrete_sequence=[VERDE])
    fig.update_traces(text=d["close_clb"].round(2), textposition="top center",
                      mode="lines+markers+text", textfont=dict(size=10))
    fig.update_layout(**_LAYOUT, height=320, xaxis_title="Vencimento",
                      yaxis_title="¢/lb")
    return fig


# ── Basis: ESALQ vs NY equivalente ────────────────────────────────────────
def fig_basis() -> go.Figure | None:
    d = _df("SELECT data_ref, esalq_rs_sc50kg, ny_equiv_rs_sc50kg "
            "FROM basis_acucar ORDER BY data_ref")
    if d.empty:
        return None
    d["data_ref"] = pd.to_datetime(d["data_ref"])
    d = d[d["data_ref"] >= d["data_ref"].max() - pd.Timedelta(days=730)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["data_ref"], y=d["esalq_rs_sc50kg"],
                             name="ESALQ (mercado interno)", mode="lines",
                             line=dict(color=VERDE, width=2)))
    fig.add_trace(go.Scatter(x=d["data_ref"], y=d["ny_equiv_rs_sc50kg"],
                             name="NY equivalente (exportação)", mode="lines",
                             line=dict(color=AMBAR, width=2)))
    fig.update_layout(**_LAYOUT, height=340,
                      legend=dict(orientation="h", y=1.02, x=0),
                      yaxis_title="R$/sc 50kg", xaxis_title="")
    return fig


# ── finviz: performance por ativo (barras) ────────────────────────────────
def fig_finviz(categoria: str | None = None) -> go.Figure | None:
    d = _df("SELECT ticker, nome, categoria, perf_ytd, perf_1y FROM finviz_perf "
            "WHERE data_coleta = (SELECT MAX(data_coleta) FROM finviz_perf)")
    if d.empty:
        return None
    if categoria:
        d = d[d["categoria"] == categoria]
    d = d.dropna(subset=["perf_ytd"]).sort_values("perf_ytd")
    if d.empty:
        return None
    d["cor"] = d["perf_ytd"].apply(lambda v: VERDE if v >= 0 else TERRACOTA)
    fig = go.Figure(go.Bar(
        x=d["perf_ytd"], y=d["nome"].fillna(d["ticker"]), orientation="h",
        marker_color=d["cor"], text=d["perf_ytd"].round(1),
        textposition="outside"))
    fig.update_layout(**_LAYOUT, height=max(300, 22 * len(d) + 60),
                      xaxis_title="Performance no ano (%)", yaxis_title="")
    return fig


def enso_atual() -> dict | None:
    d = _df("SELECT alert_status, fase_oni, trimestre_oni, oni_anom_c, nino34_c, "
            "sinopse FROM enso_status ORDER BY data_coleta DESC LIMIT 1")
    if d.empty:
        return None
    return d.iloc[0].to_dict()


def categorias_finviz() -> list[str]:
    d = _df("SELECT DISTINCT categoria FROM finviz_perf "
            "WHERE data_coleta = (SELECT MAX(data_coleta) FROM finviz_perf) "
            "AND categoria IS NOT NULL AND categoria <> '' ORDER BY categoria")
    return d["categoria"].tolist() if not d.empty else []


# ══ Bloco Etanol ══════════════════════════════════════════════════════════

def _serie_indicador(code: str, dias: int = 730) -> pd.DataFrame:
    d = _df(f"SELECT data_referencia AS d, valor AS v FROM indicator_values "
            f"WHERE indicator_code = '{code}' ORDER BY data_referencia")
    if d.empty:
        return d
    d["d"] = pd.to_datetime(d["d"])
    return d[d["d"] >= d["d"].max() - pd.Timedelta(days=dias)]


def fig_paulinia() -> go.Figure | None:
    """Hidratado Paulínia (CEPEA) — R$/m³, diário."""
    d = _serie_indicador("etanol_paulinia")
    if d.empty:
        return None
    fig = px.line(d, x="d", y="v", color_discrete_sequence=[VERDE])
    fig.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:,.0f}/m³<extra></extra>")
    fig.update_layout(**_LAYOUT, height=300, xaxis_title="", yaxis_title="R$/m³")
    return fig


def fig_b3_curva() -> go.Figure | None:
    """Curva forward do etanol na B3 — última sessão disponível."""
    d = _df("SELECT vencimento, ajuste FROM b3_eth_curva WHERE data_ref = "
            "(SELECT MAX(data_ref) FROM b3_eth_curva) AND ajuste IS NOT NULL "
            "ORDER BY vencimento")
    if d.empty:
        return None
    fig = px.line(d, x="vencimento", y="ajuste", markers=True,
                  color_discrete_sequence=[VERDE])
    fig.update_traces(text=d["ajuste"].round(0), textposition="top center",
                      mode="lines+markers+text", textfont=dict(size=11))
    fig.update_layout(**_LAYOUT, height=300, xaxis_title="Vencimento",
                      yaxis_title="R$/m³ (ajuste)")
    return fig


def fig_base_sp_go() -> go.Figure | None:
    """Base do hidratado: usina SP menos GO (R$/L)."""
    d = _df("SELECT semana_inicio, base_rs_l FROM etanol_base_sp_go "
            "ORDER BY semana_inicio")
    if d.empty:
        return None
    d["semana_inicio"] = pd.to_datetime(d["semana_inicio"])
    d = d[d["semana_inicio"] >= d["semana_inicio"].max() - pd.Timedelta(days=730)]
    fig = go.Figure(go.Scatter(
        x=d["semana_inicio"], y=d["base_rs_l"], mode="lines",
        line=dict(color=VERDE, width=2), fill="tozeroy",
        fillcolor="rgba(20,87,58,0.10)",
        hovertemplate="%{x|%d/%m/%Y}<br>Base R$ %{y:.3f}/L<extra></extra>"))
    fig.add_hline(y=0, line_color=TINTA_SUAVE, line_width=1)
    fig.update_layout(**_LAYOUT, height=300, xaxis_title="", yaxis_title="R$/L")
    return fig


def fig_abicom() -> go.Figure | None:
    """Defasagem da paridade de importação (ABICOM) — diesel e gasolina."""
    d = _df("SELECT data_ref, defasagem_diesel_pct, defasagem_gasolina_pct "
            "FROM abicom_ppi ORDER BY data_ref")
    if d.empty:
        return None
    d["data_ref"] = pd.to_datetime(d["data_ref"])
    d = d[d["data_ref"] >= d["data_ref"].max() - pd.Timedelta(days=365)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["data_ref"], y=d["defasagem_gasolina_pct"],
                             name="Gasolina", mode="lines",
                             line=dict(color=AMBAR, width=2)))
    fig.add_trace(go.Scatter(x=d["data_ref"], y=d["defasagem_diesel_pct"],
                             name="Diesel", mode="lines",
                             line=dict(color=TERRACOTA, width=2)))
    fig.add_hline(y=0, line_color=TINTA_SUAVE, line_width=1)
    fig.update_layout(**_LAYOUT, height=300, xaxis_title="",
                      yaxis_title="Defasagem (%)",
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def fig_vendas_hidratado() -> go.Figure | None:
    """Vendas mensais de etanol hidratado no Brasil (ANP)."""
    d = _serie_indicador("vendas_combustiveis", dias=1095)
    if d.empty:
        return None
    fig = px.bar(d, x="d", y="v", color_discrete_sequence=[VERDE])
    fig.update_traces(hovertemplate="%{x|%m/%Y}<br>%{y:,.0f} m³<extra></extra>")
    fig.update_layout(**_LAYOUT, height=300, xaxis_title="", yaxis_title="m³")
    return fig


def fig_basis_spread() -> go.Figure | None:
    """Spread: ESALQ menos NY equivalente (R$/sc) — prêmio do mercado interno."""
    d = _df("SELECT data_ref, esalq_rs_sc50kg, ny_equiv_rs_sc50kg FROM basis_acucar "
            "WHERE esalq_rs_sc50kg IS NOT NULL AND ny_equiv_rs_sc50kg IS NOT NULL "
            "ORDER BY data_ref")
    if d.empty:
        return None
    d["data_ref"] = pd.to_datetime(d["data_ref"])
    d = d[d["data_ref"] >= d["data_ref"].max() - pd.Timedelta(days=730)]
    d["spread"] = d["esalq_rs_sc50kg"] - d["ny_equiv_rs_sc50kg"]
    fig = go.Figure(go.Scatter(
        x=d["data_ref"], y=d["spread"], mode="lines",
        line=dict(color=VERDE, width=2), fill="tozeroy",
        fillcolor="rgba(20,87,58,0.10)",
        hovertemplate="%{x|%d/%m/%Y}<br>Base R$ %{y:,.2f}/sc<extra></extra>"))
    fig.add_hline(y=0, line_color=TINTA_SUAVE, line_width=1)
    fig.update_layout(**_LAYOUT, height=300, xaxis_title="",
                      yaxis_title="ESALQ − NY equiv. (R$/sc)")
    return fig


def fig_usda_balanco() -> go.Figure | None:
    """Balanço mundial de açúcar (USDA): produção vs consumo + estoque/uso."""
    d = _df("""SELECT data_referencia AS d, indicator_code AS c, valor AS v
               FROM indicator_values
               WHERE indicator_code IN ('usda_acucar_prod','usda_acucar_consumo',
                                        'usda_stock_to_use')
               ORDER BY data_referencia""")
    if d.empty:
        return None
    d["ano"] = pd.to_datetime(d["d"]).dt.year
    piv = d.pivot_table(index="ano", columns="c", values="v", aggfunc="last")
    if "usda_acucar_prod" not in piv.columns:
        return None
    fig = go.Figure()
    fig.add_bar(x=piv.index, y=piv["usda_acucar_prod"], name="Produção",
                marker_color=VERDE, offsetgroup="p")
    if "usda_acucar_consumo" in piv.columns:
        fig.add_bar(x=piv.index, y=piv["usda_acucar_consumo"], name="Consumo",
                    marker_color=AMBAR, offsetgroup="c")
    if "usda_stock_to_use" in piv.columns:
        fig.add_trace(go.Scatter(x=piv.index, y=piv["usda_stock_to_use"],
                                 name="Estoque/uso (%)", yaxis="y2", mode="lines+markers",
                                 line=dict(color=TERRACOTA, width=2)))
    fig.update_layout(**_LAYOUT, height=340, barmode="group",
                      yaxis_title="mil t", xaxis_title="",
                      yaxis2=dict(title="Estoque/uso (%)", overlaying="y",
                                  side="right", showgrid=False),
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig
