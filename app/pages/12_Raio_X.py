"""Página — Raio X: painel de carteira de crédito (só visualização).

Protegida pelo login individual. A carteira vive só na sessão — nunca é salva
(exceto a base de TESTE fictícia, com aviso). Comentários e de-para persistem
por ID. Visual profissional: KPIs em cards, donuts, barras empilhadas, filtros.
"""

from __future__ import annotations

import io as _io
import os as _os
import sys as _sys

_r = _os.path.abspath(_os.path.dirname(__file__))
while _r != "/" and not _os.path.isdir(_os.path.join(_r, "src")):
    _r = _os.path.dirname(_r)
if _r not in _sys.path:
    _sys.path.insert(0, _r)


import pandas as pd
import streamlit as st

from src.app_auth import exigir_login
from src.contas import usuario_logado
from src.depara import (
    aplicar_depara,
    carregar_depara,
    importar_depara_excel,
    salvar_linha_depara,
)
from src.persistence.db import init_schema
from src.raiox import (
    BUCKET_ORDER,
    aplicar_comentarios,
    calcular_pd_e_rating_medio,
    carregar_base_teste,
    excluir_base_teste,
    existe_base_teste,
    ler_carteira_excel,
    normalize_base,
    salvar_base_teste,
    salvar_comentario,
)
from src.raiox_abas import (
    build_qualidade,
    build_visitas_resumo,
    build_visitas_views,
    clientes_por_analista,
    estilizar,
    movement_available,
    table_b2_ou_pior,
    table_movement,
    table_rating_movement,
    table_top_bucket,
    vencimentos_mensais,
)
from src.raiox_visual import (
    aplicar_filtros,
    barras_por_dimensao,
    barras_setor_risco_disp,
    donut_cobertura,
    donut_por_bucket,
    fmt_int,
    fmt_mm,
    grafico_vencimentos,
    heatmap_setor_faixa,
    histograma_utilizacao,
    kpi_html,
    opcoes_filtro,
    pareto_concentracao,
    secao,
    top_concentracao,
)
from src.theme import apply_theme

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Raio X", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

# ── porteiro: só quem tem login individual aprovado ──────────────────────
u = usuario_logado()
if not u:
    st.markdown('<div class="eyebrow">Raio X — carteira de crédito</div>',
                unsafe_allow_html=True)
    st.title("Raio X")
    st.info("Esta área exige **login individual**. Entre com sua conta em "
            "**Minha conta** para acessar o Raio X.")
    st.stop()

st.markdown('<div class="eyebrow">Raio X — carteira de crédito · só visualização</div>',
            unsafe_allow_html=True)
st.title("Raio X")
st.caption("A carteira enviada vive só nesta sessão e não é salva. "
           "Apenas comentários e de-para (por cliente) ficam guardados.")

# ── carga da carteira ────────────────────────────────────────────────────
tem_base_salva = existe_base_teste()

with st.sidebar:
    st.markdown("### Carregar carteira")
    arquivo = st.file_uploader("Planilha da carteira (.xlsx)", type=["xlsx"])
    st.caption("O arquivo é processado na memória e descartado ao sair.")
    if tem_base_salva:
        if st.button("📂 Usar base de teste salva", width="stretch"):
            st.session_state["_raiox_fonte"] = "salva"
            st.rerun()
    if st.button("🧪 Carregar carteira de exemplo", width="stretch"):
        st.session_state["_raiox_fonte"] = "exemplo"
        st.rerun()

if arquivo is not None:
    st.session_state["_raiox_fonte"] = "upload"

fonte = st.session_state.get("_raiox_fonte")

try:
    if fonte == "exemplo":
        from src.raiox_exemplo import carteira_exemplo
        base = normalize_base(carteira_exemplo())
    elif fonte == "salva" and tem_base_salva:
        base = carregar_base_teste()
    elif arquivo is not None:
        base = normalize_base(ler_carteira_excel(arquivo))
    else:
        st.info("⬅️ Carregue a planilha da carteira, ou use a **base de teste** / "
                "**carteira de exemplo** na barra lateral.")
        st.stop()
    base = aplicar_depara(base)
    base = aplicar_comentarios(base)
except Exception as exc:  # noqa: BLE001
    st.error(f"Não consegui ler a planilha: {exc}")
    st.stop()

# ── base de teste: salvar/excluir + aviso ────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("### Base de teste")
    if st.button("💾 Salvar base atual como teste", width="stretch"):
        salvar_base_teste(base, u["email"])
        st.success("Base de teste salva.")
        st.rerun()
    if tem_base_salva and st.button("🗑️ Excluir base de teste", width="stretch"):
        excluir_base_teste()
        st.session_state.pop("_raiox_fonte", None)
        st.success("Base de teste excluída.")
        st.rerun()

if tem_base_salva or fonte == "salva":
    st.error("⚠️ **Base de teste salva na nuvem.** Use **apenas dados fictícios**. "
             "Nunca salve carteira real. Exclua a base de teste ao terminar.")
if fonte == "exemplo":
    st.warning("🧪 Usando **carteira de exemplo** (dados fictícios).")

# ── filtros ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("### Filtros")
    escolhas: dict[str, list[str]] = {}
    for col, rotulo, opcoes in opcoes_filtro(base):
        escolhas[col] = st.multiselect(rotulo, opcoes, key=f"filtro_{col}")

df = aplicar_filtros(base, escolhas)
filtrado = any(v for v in escolhas.values())

topo = st.columns([3, 1])
topo[0].success(f"Carteira: **{fmt_int(base['grupo'].nunique())}** grupos"
                + (f" · filtro ativo: **{fmt_int(df['grupo'].nunique())}** exibidos"
                   if filtrado else ""))
if df.empty:
    st.warning("Os filtros escolhidos não deixaram nenhum cliente. Ajuste na barra lateral.")
    st.stop()

# ── abas ─────────────────────────────────────────────────────────────────
abas = st.tabs([
    "Resumo Executivo", "Dashboard", "Comentários", "De-Para",
    "Tabelas de Rating", "Movimentações", "Próximos Vencimentos",
    "Visitas", "Clientes", "Qualidade", "Comparação M-1", "Exportar",
])

# --- Resumo Executivo ---
with abas[0]:
    pd_media, rating_medio = calcular_pd_e_rating_medio(df)
    st.markdown(kpi_html([
        ("Limite total", fmt_mm(df["limite"].sum()), "carteira exibida"),
        ("Risco total", fmt_mm(df["risco"].sum()), "carteira exibida"),
        ("Disponibilidade", fmt_mm(df["disponibilidade"].sum()), "limite – risco"),
        ("Grupos", fmt_int(df["grupo"].nunique()), "clientes exibidos"),
        ("Rating médio", rating_medio,
         f"PD média {pd_media * 100:.2f}%".replace(".", ",") if pd_media else "—"),
    ]), unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(secao("Risco por faixa de rating"), unsafe_allow_html=True)
        fig = donut_por_bucket(df, "risco", "Risco total")
        if fig:
            st.plotly_chart(fig, width="stretch")
    with c2:
        st.markdown(secao("Limite por faixa de rating"), unsafe_allow_html=True)
        fig = donut_por_bucket(df, "limite", "Limite total")
        if fig:
            st.plotly_chart(fig, width="stretch")

    st.markdown(secao("Concentração", "Top 10 grupos por risco"), unsafe_allow_html=True)
    fig = top_concentracao(df)
    if fig:
        st.plotly_chart(fig, width="stretch")

# --- Dashboard ---
with abas[1]:
    st.markdown(secao("Limite x Risco x Disponibilidade",
                      "por setor gerencial"), unsafe_allow_html=True)
    fig = barras_setor_risco_disp(df)
    if fig:
        st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(secao("Risco por analista"), unsafe_allow_html=True)
        fig = barras_por_dimensao(df, "analista", "")
        if fig:
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("Sem coluna de analista na base.")
    with c2:
        st.markdown(secao("Risco por officer"), unsafe_allow_html=True)
        fig = barras_por_dimensao(df, "officer", "")
        if fig:
            st.plotly_chart(fig, width="stretch")
        else:
            st.caption("A base não tem a coluna de officer.")

    st.markdown(secao("Risco por diretor comercial"), unsafe_allow_html=True)
    fig = barras_por_dimensao(df, "diretor_comercial", "")
    if fig:
        st.plotly_chart(fig, width="stretch")
    else:
        st.caption("A base não tem a coluna de diretor comercial.")

    st.markdown(secao("Mapa de risco", "setor gerencial × faixa de rating"),
                unsafe_allow_html=True)
    fig = heatmap_setor_faixa(df)
    if fig:
        st.plotly_chart(fig, width="stretch")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(secao("Concentração acumulada",
                          "% do risco nos N maiores grupos"), unsafe_allow_html=True)
        fig = pareto_concentracao(df)
        if fig:
            st.plotly_chart(fig, width="stretch")
    with c2:
        st.markdown(secao("Utilização do limite",
                          "distribuição de risco ÷ limite"), unsafe_allow_html=True)
        fig = histograma_utilizacao(df)
        if fig:
            st.plotly_chart(fig, width="stretch")

# --- Comentários ---
with abas[2]:
    st.markdown(secao("Comentários por cliente",
                      "ficam salvos e reaparecem quando a carteira volta"),
                unsafe_allow_html=True)
    grupos_lista = base[["id", "grupo"]].drop_duplicates().sort_values("grupo")
    rotulos = {f'{r["grupo"]} (ID {r["id"]})': r["id"] for _, r in grupos_lista.iterrows()}
    escolha = st.selectbox("Cliente", list(rotulos.keys()))
    if escolha:
        cid = rotulos[escolha]
        atual = base[base["id"] == cid].iloc[0]
        novo_status = st.text_input("Status", value=str(atual.get("status", "") or ""))
        novo_com = st.text_area("Comentário",
                                value=str(atual.get("comentario", "") or ""), height=120)
        if st.button("Salvar comentário", type="primary"):
            salvar_comentario(cid, novo_status, novo_com, u["email"])
            st.success("Comentário salvo.")

# --- De-Para ---
with abas[3]:
    st.markdown(secao("De-Para", "setor gerencial, ativo/inativo e ajuste de analista"),
                unsafe_allow_html=True)
    with st.expander("Importar de-para de uma planilha (.xlsx)"):
        arq_dep = st.file_uploader("Planilha de de-para", type=["xlsx"], key="dep_upload")
        if arq_dep is not None and st.button("Importar de-para"):
            n, msg = importar_depara_excel(arq_dep, u["email"])
            (st.success if n else st.error)(msg)
            if n:
                st.rerun()

    st.markdown("**Editar um cliente**")
    st.caption("O analista e o setor vêm da base. Se mudar aqui, o de-para passa a "
               "valer para esse cliente; se deixar como está, continua o da base.")
    grupos_dep = base[["id", "grupo"]].drop_duplicates().sort_values("grupo")
    rot_dep = {f'{r["grupo"]} (ID {r["id"]})': r["id"] for _, r in grupos_dep.iterrows()}
    if rot_dep:
        esc = st.selectbox("Cliente", list(rot_dep.keys()), key="dep_cliente")
        cid = rot_dep[esc]
        linha = base[base["id"] == cid].iloc[0]
        col_a, col_b = st.columns(2)
        with col_a:
            novo_analista = st.text_input(
                "Analista", value=str(linha.get("analista", "") or ""),
                help="Vem da base. Edite só se quiser sobrescrever.")
        with col_b:
            novo_setor = st.text_input(
                "Setor gerencial", value=str(linha.get("setor_gerencial", "") or ""))
        ativo = st.checkbox("Cliente ativo", value=True)
        if st.button("Salvar de-para deste cliente", type="primary"):
            salvar_linha_depara(cid, novo_analista, novo_setor, 1 if ativo else 0,
                                u["email"], grupo=str(linha.get("grupo", "") or ""))
            st.success("De-para salvo.")

    dep_salvo = carregar_depara()
    if not dep_salvo.empty:
        st.markdown(f"**De-para salvo · {fmt_int(len(dep_salvo))} clientes**")
        tabela = dep_salvo.copy()
        tabela["id_cliente"] = tabela["id_cliente"].astype(str).str.strip()
        tabela = tabela.rename(columns={"analista": "analista_dep"})
        analista_base = base[["id", "analista"]].copy()
        analista_base["id"] = analista_base["id"].astype(str).str.strip()
        analista_base = analista_base.rename(columns={"analista": "analista_base"})
        tabela = tabela.merge(analista_base, left_on="id_cliente", right_on="id", how="left")
        dep_txt = tabela["analista_dep"].fillna("").astype(str).str.strip()
        dep_vazio = dep_txt.str.lower().isin(["", "none", "nan", "null"])
        tabela["analista"] = tabela["analista_base"].where(dep_vazio, tabela["analista_dep"])
        tabela = tabela[["id_cliente", "grupo", "analista", "setor_gerencial", "ativo"]]
        st.dataframe(tabela, width="stretch", hide_index=True)

# --- Tabelas de Rating ---
with abas[4]:
    st.markdown(secao("Tabelas por faixa de rating",
                      "top 10 por limite em cada faixa, com totais"),
                unsafe_allow_html=True)
    for faixa in BUCKET_ORDER:
        t = table_top_bucket(df, faixa)
        if not t.empty:
            st.markdown(f"**{faixa}**")
            st.dataframe(estilizar(t), width="stretch", hide_index=True)
    t_b2 = table_b2_ou_pior(df)
    if not t_b2.empty:
        st.markdown("**B2 ou pior · top 10 por risco**")
        st.dataframe(estilizar(t_b2), width="stretch", hide_index=True)

# --- Movimentações ---
with abas[5]:
    st.markdown(secao("Movimentações do mês"), unsafe_allow_html=True)
    if not movement_available(df):
        st.info("A base carregada não tem as colunas de comparação com o mês "
                "anterior (delta de limite, risco e rating).")
    else:
        blocos = [
            ("Aumento de limite · Top 10", table_movement(df, "limite", "up")),
            ("Redução de limite · Top 10", table_movement(df, "limite", "down")),
            ("Aumento de risco · Top 10", table_movement(df, "risco", "up")),
            ("Redução de risco · Top 10", table_movement(df, "risco", "down")),
            ("Upgrades de rating", table_rating_movement(df, "upgrade")),
            ("Downgrades de rating", table_rating_movement(df, "downgrade")),
        ]
        for titulo, tb in blocos:
            st.markdown(f"**{titulo}**")
            if tb.empty:
                st.caption("Nenhum registro nesta categoria.")
            else:
                st.dataframe(estilizar(tb), width="stretch", hide_index=True)

# --- Próximos Vencimentos ---
with abas[6]:
    st.markdown(secao("Próximos vencimentos de limite",
                      "a partir do mês vigente (vira no dia 5)"),
                unsafe_allow_html=True)
    venc = vencimentos_mensais(df)
    if venc.empty:
        st.info("A base carregada não tem vencimentos de limite no período "
                "(ou não tem a coluna de data de vencimento).")
    else:
        fig = grafico_vencimentos(venc)
        if fig:
            st.plotly_chart(fig, width="stretch")
        tab = venc.copy()
        tab["Risco (R$ mm)"] = tab["Risco"] / 1_000_000
        st.dataframe(estilizar(tab[["Período", "Grupos", "Renovação automática",
                                     "Risco (R$ mm)"]]),
                     width="stretch", hide_index=True)

# --- Visitas ---
with abas[7]:
    st.markdown(secao("Visitas", "política: Ba4+ até 12 meses · Ba6- até 6 meses"),
                unsafe_allow_html=True)
    resumo_vis = build_visitas_resumo(df)
    if resumo_vis.empty:
        st.info("A base carregada não tem rating/data de visita para esta análise.")
    else:
        fora = resumo_vis[resumo_vis["Categoria"] != "Em dia"]
        risco_fora = fora["Risco"].sum()
        grupos_fora = int(fora["Grupos"].sum())
        risco_total = resumo_vis["Risco"].sum()
        grupos_total = int(resumo_vis["Grupos"].sum())
        st.markdown(kpi_html([
            ("Risco · visita pendente", fmt_mm(risco_fora),
             f"{risco_fora / risco_total:.0%} da carteira".replace(".", ",")
             if risco_total else "—"),
            ("Grupos · visita pendente", fmt_int(grupos_fora),
             f"{grupos_fora / grupos_total:.0%} da carteira".replace(".", ",")
             if grupos_total else "—"),
        ]), unsafe_allow_html=True)

        g1, g2 = st.columns(2)
        with g1:
            fig = donut_cobertura(resumo_vis, "Risco", "% Risco",
                                  "Cobertura · por risco")
            if fig:
                st.plotly_chart(fig, width="stretch")
        with g2:
            fig = donut_cobertura(resumo_vis, "Grupos", "% Grupos",
                                  "Cobertura · por grupos")
            if fig:
                st.plotly_chart(fig, width="stretch")

        sem_df, ba4_df, ba6_df = build_visitas_views(df)
        _ren = {"id": "ID", "grupo": "Grupo", "analista": "Analista",
                "rating": "Rating", "limite": "Limite (R$ mm)",
                "risco": "Risco (R$ mm)", "data_visita": "Última visita",
                "meses_sem_visita": "Meses sem visita"}

        st.markdown(f"**Grupos sem visita · {len(sem_df)}**")
        if sem_df.empty:
            st.caption("Não há grupos sem visita.")
        else:
            st.dataframe(estilizar(sem_df.rename(columns=_ren)),
                         width="stretch", hide_index=True)

        st.markdown(f"**Ba4 ou acima com 12+ meses sem visita · {len(ba4_df)}**")
        if ba4_df.empty:
            st.caption("Nenhum cliente nesta condição.")
        else:
            st.dataframe(estilizar(ba4_df.rename(columns=_ren)),
                         width="stretch", hide_index=True)

        st.markdown(f"**Ba6 ou abaixo com 6+ meses sem visita · {len(ba6_df)}**")
        if ba6_df.empty:
            st.caption("Nenhum cliente nesta condição.")
        else:
            st.dataframe(estilizar(ba6_df.rename(columns=_ren)),
                         width="stretch", hide_index=True)

# --- Clientes ---
with abas[8]:
    st.markdown(secao("Clientes por analista"), unsafe_allow_html=True)
    resumo_cli = clientes_por_analista(df)
    if resumo_cli.empty:
        st.info("A base carregada não tem a coluna de analista.")
    else:
        st.dataframe(estilizar(resumo_cli), width="stretch", hide_index=True)
        st.markdown("**Ver clientes de um analista**")
        analista_sel = st.selectbox("Analista", resumo_cli["Analista"].tolist(),
                                    key="cli_analista")
        det = df[df["analista"].astype(str) == str(analista_sel)].copy()
        det = det.sort_values("risco", ascending=False)
        cols = [c for c in ["id", "grupo", "setor_gerencial", "rating", "limite",
                            "risco", "disponibilidade", "data_visita",
                            "status", "comentario"] if c in det.columns]
        mostra = det[cols].rename(columns={
            "id": "ID", "grupo": "Grupo", "setor_gerencial": "Setor",
            "rating": "Rating", "limite": "Limite", "risco": "Risco",
            "disponibilidade": "Disponível", "data_visita": "Data visita",
            "status": "Status", "comentario": "Comentário"})
        st.dataframe(estilizar(mostra), width="stretch", hide_index=True)

# --- Qualidade ---
with abas[9]:
    st.markdown(secao("Qualidade e pendências da base"), unsafe_allow_html=True)
    resumo_q, detalhes_q = build_qualidade(df)
    if resumo_q.empty:
        st.info("Nenhuma checagem de qualidade disponível para esta base.")
    else:
        st.markdown(kpi_html([
            ("Tipos de pendência", fmt_int(int((resumo_q["Qtd"] > 0).sum())), ""),
            ("Ocorrências", fmt_int(int(resumo_q["Qtd"].sum())), ""),
            ("Risco envolvido", fmt_mm(resumo_q["Risco (R$ mm)"].sum() * 1_000_000), ""),
        ]), unsafe_allow_html=True)
        st.dataframe(estilizar(resumo_q), width="stretch", hide_index=True)
        st.markdown("**Ver clientes de uma pendência**")
        pend = st.selectbox("Pendência", resumo_q["Pendência"].tolist(), key="q_pend")
        det = detalhes_q.get(pend, None)
        if det is not None and not det.empty:
            st.dataframe(estilizar(det.rename(columns={
                "id": "ID", "grupo": "Grupo", "analista": "Analista",
                "setor_gerencial": "Setor", "rating": "Rating",
                "limite": "Limite", "risco": "Risco", "data_visita": "Data visita"})),
                width="stretch", hide_index=True)
        else:
            st.caption("Nenhum cliente nesta pendência.")

# --- Comparação M-1 ---
with abas[10]:
    st.markdown(secao("Comparação com o mês anterior"), unsafe_allow_html=True)
    if not movement_available(df):
        st.info("A base carregada não traz as colunas de M-1.")
    else:
        lim_atual = df["limite"].sum()
        lim_ant = df["limite_m1"].sum() if "limite_m1" in df.columns else 0
        ris_atual = df["risco"].sum()
        ris_ant = df["risco_m1"].sum() if "risco_m1" in df.columns else 0
        st.markdown(kpi_html([
            ("Limite atual", fmt_mm(lim_atual), f"Δ {fmt_mm(lim_atual - lim_ant)}"),
            ("Risco atual", fmt_mm(ris_atual), f"Δ {fmt_mm(ris_atual - ris_ant)}"),
        ]), unsafe_allow_html=True)
        st.markdown("**Maiores variações de risco no mês**")
        if "delta_risco" in df.columns:
            var = df[["grupo", "rating", "delta_risco", "risco"]].copy()
            var = var[var["delta_risco"].abs() > 0].sort_values(
                "delta_risco", key=abs, ascending=False).head(15)
            st.dataframe(estilizar(var.rename(columns={
                "grupo": "Grupo", "rating": "Rating",
                "delta_risco": "Delta Risco (R$ mm)", "risco": "Risco (R$ mm)"})),
                width="stretch", hide_index=True)

# --- Exportar ---
with abas[11]:
    st.markdown(secao("Exportar a carteira",
                      "com de-para, comentários e filtros aplicados"),
                unsafe_allow_html=True)
    buf = _io.BytesIO()
    cols_exp = [c for c in ["id", "grupo", "analista", "setor_gerencial", "officer",
                            "diretor_comercial", "rating", "bucket_rating", "limite",
                            "risco", "disponibilidade", "data_visita",
                            "status", "comentario"] if c in df.columns]
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df[cols_exp].to_excel(writer, index=False, sheet_name="Carteira")
    st.download_button(
        "📥 Baixar carteira em Excel", data=buf.getvalue(),
        file_name="carteira_raio_x.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
