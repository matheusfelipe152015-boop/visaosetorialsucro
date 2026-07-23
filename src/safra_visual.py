"""Gráficos da UNICA para a aba Safra — moagem, mix e ATR do Centro-Sul.

Lê o CSV quinzenal da UNICA (via coletor sugar-intel) direto da fonte, para
ter a granularidade quinzenal da safra corrente. As visões: evolução da moagem
acumulada, do mix açúcar/etanol e do ATR médio.
"""

from __future__ import annotations

import csv
import io

import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

VERDE = "#14573A"
AMBAR = "#C6881C"
TINTA = "#18241F"
LINHA = "#E6E2D6"
CSV_URL = "https://strongylis.github.io/sugar-intel/data/unica_quinzenal.csv"
_HEADERS = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/126.0.0.0 Safari/537.36")}

_LAYOUT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
               font=dict(color=TINTA), margin=dict(l=10, r=10, t=30, b=10))


def _num(v):
    s = str(v or "").strip().replace(",", "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def carregar_unica(texto: str | None = None) -> pd.DataFrame:
    """Lê o CSV quinzenal da UNICA (baixa se texto não for passado)."""
    if texto is None:
        resp = httpx.get(CSV_URL, timeout=60, follow_redirects=True, headers=_HEADERS)
        resp.raise_for_status()
        texto = resp.content.decode("utf-8", errors="replace")
    linhas = []
    for r in csv.DictReader(io.StringIO(texto)):
        linhas.append({
            "safra": (r.get("safra") or "").strip(),
            "quinzena_fim": (r.get("quinzena_fim") or "").strip(),
            "regiao": (r.get("regiao") or "").strip(),
            "tipo_secao": (r.get("tipo_secao") or "").strip(),
            "cana_mil_t": _num(r.get("cana_mil_t")),
            "acucar_mil_t": _num(r.get("acucar_mil_t")),
            "etanol_total_mil_m3": _num(r.get("etanol_total_mil_m3")),
            "atr_kg_t_cana": _num(r.get("atr_kg_t_cana")),
            "mix_acucar_pct": _num(r.get("mix_acucar_pct")),
            "mix_etanol_pct": _num(r.get("mix_etanol_pct")),
        })
    df = pd.DataFrame(linhas)
    if not df.empty:
        df["quinzena_fim"] = pd.to_datetime(df["quinzena_fim"], errors="coerce")
    return df


def _centro_sul_acumulado(df: pd.DataFrame) -> pd.DataFrame:
    d = df[(df["regiao"] == "Centro-Sul") & (df["tipo_secao"] == "acumulado")].copy()
    return d.sort_values("quinzena_fim")


def fig_moagem(df: pd.DataFrame) -> go.Figure | None:
    d = _centro_sul_acumulado(df).dropna(subset=["cana_mil_t"])
    if d.empty:
        return None
    d["safra_lbl"] = d["safra"]
    fig = px.bar(d, x="safra_lbl", y="cana_mil_t", color_discrete_sequence=[VERDE],
                 text=(d["cana_mil_t"] / 1000).round(1))
    fig.update_traces(texttemplate="%{text} mi t", textposition="outside")
    fig.update_layout(**_LAYOUT, height=320, xaxis_title="Safra",
                      yaxis_title="Cana moída (mil t)")
    return fig


def fig_mix(df: pd.DataFrame) -> go.Figure | None:
    d = _centro_sul_acumulado(df).dropna(subset=["mix_acucar_pct"])
    if d.empty:
        return None
    fig = go.Figure()
    fig.add_bar(x=d["safra"], y=d["mix_acucar_pct"], name="Açúcar",
                marker_color=VERDE, text=d["mix_acucar_pct"].round(1),
                textposition="inside")
    fig.add_bar(x=d["safra"], y=d["mix_etanol_pct"], name="Etanol",
                marker_color=AMBAR, text=d["mix_etanol_pct"].round(1),
                textposition="inside")
    fig.update_layout(**_LAYOUT, height=320, barmode="stack",
                      yaxis_title="Mix (%)", xaxis_title="Safra",
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def fig_atr(df: pd.DataFrame) -> go.Figure | None:
    d = _centro_sul_acumulado(df).dropna(subset=["atr_kg_t_cana"])
    if d.empty:
        return None
    fig = px.line(d, x="safra", y="atr_kg_t_cana", markers=True,
                  color_discrete_sequence=[VERDE])
    fig.update_traces(text=d["atr_kg_t_cana"].round(1), textposition="top center",
                      mode="lines+markers+text")
    fig.update_layout(**_LAYOUT, height=320, yaxis_title="ATR (kg/t cana)",
                      xaxis_title="Safra")
    return fig


def resumo_safra_atual(df: pd.DataFrame) -> dict | None:
    d = _centro_sul_acumulado(df)
    if d.empty:
        return None
    ult = d.iloc[-1]
    return {
        "safra": ult["safra"],
        "cana_mil_t": ult["cana_mil_t"],
        "acucar_mil_t": ult["acucar_mil_t"],
        "etanol_mil_m3": ult["etanol_total_mil_m3"],
        "atr": ult["atr_kg_t_cana"],
        "mix_acucar": ult["mix_acucar_pct"],
    }


# ── séries do banco: oferta × demanda mensal e etanol de milho ────────────

def _df_sql(sql: str) -> pd.DataFrame:
    from sqlalchemy import text as _text

    from src.persistence.db import get_engine
    with get_engine(readonly=True).connect() as conn:
        return pd.read_sql_query(_text(sql), conn)


def fig_snd_mensal() -> go.Figure | None:
    """Entradas (produção) vs saídas (vendas) mensais de etanol + estoque."""
    d = _df_sql("""SELECT serie, data_ref, valor FROM unica_snd
                   WHERE serie IN ('Inflows Total (bi L)','Outflows Total (bi L)',
                                   'Stock accumulated (bi L)')
                   ORDER BY data_ref""")
    if d.empty:
        return None
    d["data_ref"] = pd.to_datetime(d["data_ref"])
    piv = d.pivot_table(index="data_ref", columns="serie", values="valor",
                        aggfunc="last").sort_index()
    piv = piv[piv.index >= piv.index.max() - pd.Timedelta(days=760)]
    fig = go.Figure()
    if "Inflows Total (bi L)" in piv.columns:
        fig.add_bar(x=piv.index, y=piv["Inflows Total (bi L)"], name="Produção",
                    marker_color=VERDE, offsetgroup="i")
    if "Outflows Total (bi L)" in piv.columns:
        fig.add_bar(x=piv.index, y=piv["Outflows Total (bi L)"], name="Vendas",
                    marker_color=AMBAR, offsetgroup="o")
    if "Stock accumulated (bi L)" in piv.columns:
        fig.add_trace(go.Scatter(x=piv.index, y=piv["Stock accumulated (bi L)"],
                                 name="Estoque acumulado", yaxis="y2",
                                 mode="lines", line=dict(color="#B4462E", width=2)))
    fig.update_layout(**_LAYOUT, height=340, barmode="group",
                      yaxis_title="bi L no mês", xaxis_title="",
                      yaxis2=dict(title="Estoque (bi L)", overlaying="y",
                                  side="right", showgrid=False),
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def fig_etanol_milho() -> go.Figure | None:
    """Produção de etanol de milho no Brasil, por safra (anidro + hidratado)."""
    d = _df_sql("""SELECT indicator_code AS c, data_referencia AS d, valor AS v
                   FROM indicator_values
                   WHERE indicator_code IN ('etanol_milho_anidro',
                                            'etanol_milho_hidratado')
                   ORDER BY data_referencia""")
    if d.empty:
        return None
    d["safra"] = pd.to_datetime(d["d"]).dt.year.astype(str)
    piv = d.pivot_table(index="safra", columns="c", values="v", aggfunc="last")
    fig = go.Figure()
    rotulos = {"etanol_milho_anidro": ("Anidro", VERDE),
               "etanol_milho_hidratado": ("Hidratado", AMBAR)}
    for code, (nome, cor) in rotulos.items():
        if code in piv.columns:
            fig.add_bar(x=piv.index, y=piv[code] / 1_000_000, name=nome,
                        marker_color=cor)
    fig.update_layout(**_LAYOUT, height=320, barmode="stack",
                      yaxis_title="bilhões de litros", xaxis_title="Safra (ano inicial)",
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def _snd(series: list[str]) -> pd.DataFrame:
    """Séries mensais da UNICA (tabela unica_snd) em formato de colunas."""
    lista = ",".join(f"'{s}'" for s in series)
    d = _df_sql(f"SELECT serie, data_ref, valor FROM unica_snd "
                f"WHERE serie IN ({lista}) ORDER BY data_ref")
    if d.empty:
        return d
    d["data_ref"] = pd.to_datetime(d["data_ref"])
    return d.pivot_table(index="data_ref", columns="serie", values="valor",
                         aggfunc="last").sort_index()


def fig_snd_moagem_mix() -> go.Figure | None:
    """Moagem e açúcar produzidos por mês, com o mix no eixo direito."""
    piv = _snd(["Cane crush (Mt)", "Sugar (Mt)", "Sugar mix (%)"])
    if piv.empty:
        return None
    fig = go.Figure()
    if "Cane crush (Mt)" in piv.columns:
        fig.add_bar(x=piv.index, y=piv["Cane crush (Mt)"], name="Cana moída",
                    marker_color=VERDE, offsetgroup="c")
    if "Sugar (Mt)" in piv.columns:
        fig.add_bar(x=piv.index, y=piv["Sugar (Mt)"], name="Açúcar",
                    marker_color=AMBAR, offsetgroup="a")
    if "Sugar mix (%)" in piv.columns:
        fig.add_trace(go.Scatter(x=piv.index, y=piv["Sugar mix (%)"],
                                 name="Mix açúcar (%)", yaxis="y2", mode="lines",
                                 line=dict(color="#B4462E", width=2)))
    fig.update_layout(**_LAYOUT, height=340, barmode="group",
                      yaxis_title="milhões de toneladas", xaxis_title="",
                      yaxis2=dict(title="Mix (%)", overlaying="y", side="right",
                                  showgrid=False),
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def fig_snd_anidro_hidratado() -> go.Figure | None:
    """Produção mensal de etanol separada em anidro e hidratado."""
    piv = _snd(["Inflows Anhydrous (bi L)", "Inflows Hydrous (bi L)"])
    if piv.empty:
        return None
    fig = go.Figure()
    rotulos = {"Inflows Anhydrous (bi L)": ("Anidro", VERDE),
               "Inflows Hydrous (bi L)": ("Hidratado", AMBAR)}
    for col, (nome, cor) in rotulos.items():
        if col in piv.columns:
            fig.add_bar(x=piv.index, y=piv[col], name=nome, marker_color=cor)
    fig.update_layout(**_LAYOUT, height=320, barmode="stack",
                      yaxis_title="bi L no mês", xaxis_title="",
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def fig_snd_atr() -> go.Figure | None:
    """ATR médio mensal (kg por tonelada de cana)."""
    piv = _snd(["Avg ATR (kg/t)"])
    if piv.empty or "Avg ATR (kg/t)" not in piv.columns:
        return None
    fig = px.line(x=piv.index, y=piv["Avg ATR (kg/t)"], markers=True,
                  color_discrete_sequence=[VERDE])
    fig.update_layout(**_LAYOUT, height=300, xaxis_title="",
                      yaxis_title="ATR (kg/t cana)")
    return fig


def _serie_snd(nomes: list[str]) -> pd.DataFrame:
    lista = ",".join(f"'{n}'" for n in nomes)
    d = _df_sql(f"SELECT serie, data_ref, valor FROM unica_snd WHERE serie IN ({lista})")
    if d.empty:
        return d
    d["data_ref"] = pd.to_datetime(d["data_ref"])
    return d.pivot_table(index="data_ref", columns="serie", values="valor",
                         aggfunc="last").sort_index()


def fig_moagem_mensal() -> go.Figure | None:
    """Cana moída mês a mês, com o mix de açúcar sobreposto."""
    piv = _serie_snd(["Cane crush (Mt)", "Sugar mix (%)"])
    if piv.empty or "Cane crush (Mt)" not in piv.columns:
        return None
    fig = go.Figure()
    fig.add_bar(x=piv.index, y=piv["Cane crush (Mt)"], name="Cana moída",
                marker_color=VERDE)
    if "Sugar mix (%)" in piv.columns:
        fig.add_trace(go.Scatter(x=piv.index, y=piv["Sugar mix (%)"],
                                 name="Mix açúcar", yaxis="y2", mode="lines+markers",
                                 line=dict(color=AMBAR, width=2)))
    fig.update_layout(**_LAYOUT, height=320, yaxis_title="Mt no mês", xaxis_title="",
                      yaxis2=dict(title="Mix açúcar (%)", overlaying="y",
                                  side="right", showgrid=False),
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def fig_atr_chuva_mensal() -> go.Figure | None:
    """ATR médio do mês contra a chuva no Centro-Sul."""
    piv = _serie_snd(["Avg ATR (kg/t)", "Rainfall CS (mm)"])
    if piv.empty or "Avg ATR (kg/t)" not in piv.columns:
        return None
    fig = go.Figure()
    if "Rainfall CS (mm)" in piv.columns:
        fig.add_bar(x=piv.index, y=piv["Rainfall CS (mm)"], name="Chuva (CS)",
                    marker_color="#9FC0D4", yaxis="y2")
    fig.add_trace(go.Scatter(x=piv.index, y=piv["Avg ATR (kg/t)"], name="ATR médio",
                             mode="lines+markers", line=dict(color=VERDE, width=2.5)))
    fig.update_layout(**_LAYOUT, height=320, yaxis_title="ATR (kg/t)", xaxis_title="",
                      yaxis2=dict(title="Chuva (mm)", overlaying="y", side="right",
                                  showgrid=False),
                      legend=dict(orientation="h", y=1.02, x=0))
    return fig


def fig_acucar_mensal() -> go.Figure | None:
    """Produção mensal de açúcar (Mt)."""
    piv = _serie_snd(["Sugar (Mt)"])
    if piv.empty or "Sugar (Mt)" not in piv.columns:
        return None
    fig = px.bar(x=piv.index, y=piv["Sugar (Mt)"], color_discrete_sequence=[AMBAR])
    fig.update_traces(hovertemplate="%{x|%m/%Y}<br>%{y:.2f} Mt<extra></extra>")
    fig.update_layout(**_LAYOUT, height=300, yaxis_title="Mt no mês", xaxis_title="")
    return fig
