"""Página — Raio X: painel de carteira de crédito (só visualização).

Protegida pelo login individual: só quem está logado e aprovado vê. A carteira
é enviada por upload e vive só na sessão — NUNCA é salva. O único dado que
persiste é o comentário por cliente (ligado ao ID), guardado no banco.

Esta é a primeira fase da integração: upload + Resumo Executivo + Dashboard +
comentários. As demais abas vêm nas próximas fases.
"""

from __future__ import annotations

import os as _os
import sys as _sys

_r = _os.path.abspath(_os.path.dirname(__file__))
while _r != "/" and not _os.path.isdir(_os.path.join(_r, "src")):
    _r = _os.path.dirname(_r)
if _r not in _sys.path:
    _sys.path.insert(0, _r)


import pandas as pd
import plotly.express as px
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
    ler_carteira_excel,
    normalize_base,
    salvar_comentario,
)
from src.raiox_abas import estilizar
from src.theme import apply_theme

st.set_page_config(page_title="VISÃO SETORIAL SUCRO · Raio X", page_icon="⬡", layout="wide")
exigir_login()
init_schema()
apply_theme()

# ── porteiro: só quem tem login individual aprovado ──────────────────────
u = usuario_logado()
if not u:
    st.markdown('<div class="eyebrow">Raio X — carteira de crédito</div>', unsafe_allow_html=True)
    st.title("Raio X")
    st.info("Esta área exige **login individual**. Entre com sua conta em **Minha conta** "
            "para acessar o Raio X.")
    st.stop()


def _fmt_mm(x) -> str:
    """Formata em milhões de reais, padrão brasileiro."""
    try:
        return f"R$ {float(x):,.1f} mm".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "-"


st.markdown('<div class="eyebrow">Raio X — carteira de crédito · só visualização</div>',
            unsafe_allow_html=True)
st.title("Raio X")
st.caption("A carteira enviada vive só nesta sessão e não é salva. "
           "Apenas os comentários (por cliente) ficam guardados.")

# ── upload da carteira (na sessão) ───────────────────────────────────────
from src.raiox import (
    carregar_base_teste,
    excluir_base_teste,
    existe_base_teste,
    salvar_base_teste,
)

tem_base_salva = existe_base_teste()

with st.sidebar:
    st.markdown("### Carregar carteira")
    arquivo = st.file_uploader("Planilha da carteira (.xlsx)", type=["xlsx"])
    st.caption("O arquivo é processado na memória e descartado ao sair.")

    if tem_base_salva:
        st.markdown("---")
        if st.button("📂 Usar base de teste salva"):
            st.session_state["_raiox_fonte"] = "salva"
            st.rerun()

    st.markdown("---")
    # TEMPORÁRIO (testes): carteira fictícia embutida.
    usar_exemplo = st.button("🧪 Carregar carteira de exemplo")
    st.caption("Dados fictícios, só para testar. Remover depois.")

if usar_exemplo:
    st.session_state["_raiox_fonte"] = "exemplo"
if arquivo is not None:
    st.session_state["_raiox_fonte"] = "upload"

fonte = st.session_state.get("_raiox_fonte")

# lê e normaliza (na memória)
try:
    if fonte == "exemplo":
        from src.raiox_exemplo import carteira_exemplo
        base = normalize_base(carteira_exemplo())
    elif fonte == "salva" and tem_base_salva:
        base = carregar_base_teste()   # já vem normalizada
    elif arquivo is not None:
        base = normalize_base(ler_carteira_excel(arquivo))
    else:
        st.info("⬅️ Carregue a planilha da carteira, ou use a **carteira de exemplo** "
                "na barra lateral para testar.")
        st.stop()
    base = aplicar_depara(base)          # aplica o de-para salvo (analista/setor/ativo)
    base = aplicar_comentarios(base)
except Exception as exc:  # noqa: BLE001
    st.error(f"Não consegui ler a planilha: {exc}")
    st.stop()

# ── salvar / excluir base de teste (com aviso de segurança) ──────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("### Base de teste")
    if st.button("💾 Salvar base atual como teste"):
        salvar_base_teste(base, u["email"])
        st.success("Base de teste salva.")
        st.rerun()
    if tem_base_salva and st.button("🗑️ Excluir base de teste"):
        excluir_base_teste()
        st.session_state.pop("_raiox_fonte", None)
        st.success("Base de teste excluída.")
        st.rerun()

# aviso permanente de segurança quando há base salva na nuvem
if tem_base_salva or fonte == "salva":
    st.error("⚠️ **Base de teste salva na nuvem.** Use **apenas dados fictícios** "
             "aqui. Nunca salve carteira real. Exclua a base de teste ao terminar.")

if fonte == "exemplo":
    st.warning("🧪 Usando **carteira de exemplo** (dados fictícios, só para teste).")
st.success(f"Carteira carregada: **{len(base)}** clientes.")

# ── abas ─────────────────────────────────────────────────────────────────
abas = st.tabs([
    "Resumo Executivo", "Dashboard", "Comentários", "De-Para",
    "Tabelas de Rating", "Movimentações", "Próximos Vencimentos",
    "Visitas", "Clientes", "Qualidade", "Comparação M-1", "Exportar PDF",
])

# --- Resumo Executivo ---
with abas[0]:
    limite = base["limite"].sum()
    risco = base["risco"].sum()
    disp = base["disponibilidade"].sum()
    grupos = base["grupo"].nunique()
    pd_media, rating_medio = calcular_pd_e_rating_medio(base)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Limite total", _fmt_mm(limite))
    c2.metric("Risco total", _fmt_mm(risco))
    c3.metric("Disponibilidade", _fmt_mm(disp))
    c4.metric("Grupos", f"{grupos}")
    c5.metric("Rating médio", rating_medio)

    st.markdown("---")
    st.markdown("##### Risco por faixa de rating")
    if "bucket_rating" in base.columns:
        por_faixa = (
            base.groupby("bucket_rating")["risco"].sum()
            .reindex(BUCKET_ORDER).dropna().reset_index()
        )
        if not por_faixa.empty:
            fig = px.bar(por_faixa, x="bucket_rating", y="risco",
                         labels={"bucket_rating": "Faixa", "risco": "Risco (R$)"},
                         color_discrete_sequence=["#14573A"])
            st.plotly_chart(fig, width="stretch")

# --- Dashboard ---
with abas[1]:
    st.markdown("##### Risco por setor gerencial")
    por_setor = (
        base.groupby("setor_gerencial")["risco"].sum()
        .sort_values(ascending=False).head(15).reset_index()
    )
    if not por_setor.empty:
        fig = px.bar(por_setor, x="risco", y="setor_gerencial", orientation="h",
                     labels={"risco": "Risco (R$)", "setor_gerencial": "Setor"},
                     color_discrete_sequence=["#14573A"])
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")

    st.markdown("##### Maiores riscos (top 15 grupos)")
    top = base.groupby("grupo")["risco"].sum().sort_values(ascending=False).head(15)
    st.dataframe(top.reset_index().rename(columns={"grupo": "Grupo", "risco": "Risco"}),
                 width="stretch", hide_index=True)

# --- Comentários (o dado que persiste) ---
with abas[2]:
    st.markdown("##### Comentários por cliente")
    st.caption("O comentário fica salvo e reaparece quando você subir a carteira de novo. "
               "A carteira em si não é salva.")
    grupos_lista = base[["id", "grupo"]].drop_duplicates().sort_values("grupo")
    rotulos = {f'{r["grupo"]} (ID {r["id"]})': r["id"]
               for _, r in grupos_lista.iterrows()}
    escolha = st.selectbox("Cliente", list(rotulos.keys()))
    if escolha:
        cid = rotulos[escolha]
        atual = base[base["id"] == cid].iloc[0]
        novo_status = st.text_input("Status", value=str(atual.get("status", "") or ""))
        novo_com = st.text_area("Comentário",
                                value=str(atual.get("comentario", "") or ""), height=120)
        if st.button("Salvar comentário", type="primary"):
            salvar_comentario(cid, novo_status, novo_com, u["email"])
            st.success("Comentário salvo. Reaparece na próxima vez que subir a carteira.")

# --- De-Para (editável, salvo no banco) ---
with abas[3]:
    st.markdown("##### De-Para — analista, setor e ativo/inativo por cliente")
    st.caption("O de-para fica salvo (é só configuração, sem dado de crédito). "
               "É aplicado sobre a carteira: muda analista/setor e remove os inativos.")

    with st.expander("Importar de-para de uma planilha (.xlsx)"):
        arq_dep = st.file_uploader("Planilha de de-para", type=["xlsx"], key="dep_upload")
        if arq_dep is not None and st.button("Importar de-para"):
            n, msg = importar_depara_excel(arq_dep, u["email"])
            (st.success if n else st.error)(msg)
            if n:
                st.rerun()

    st.markdown("**Editar um cliente**")
    st.caption("O analista e o setor já vêm preenchidos com o que está na base. "
               "Se você mudar aqui, o de-para passa a valer para esse cliente. "
               "Se deixar como está, continua o da base.")
    grupos_dep = base[["id", "grupo"]].drop_duplicates().sort_values("grupo")
    rot_dep = {f'{r["grupo"]} (ID {r["id"]})': r["id"] for _, r in grupos_dep.iterrows()}
    if rot_dep:
        esc = st.selectbox("Cliente", list(rot_dep.keys()), key="dep_cliente")
        cid = rot_dep[esc]
        linha = base[base["id"] == cid].iloc[0]
        col_a, col_b = st.columns(2)
        with col_a:
            novo_analista = st.text_input("Analista", value=str(linha.get("analista", "") or ""),
                                          help="Vem da base. Edite só se quiser sobrescrever.")
        with col_b:
            novo_setor = st.text_input("Setor gerencial",
                                       value=str(linha.get("setor_gerencial", "") or ""))
        ativo = st.checkbox("Cliente ativo", value=True)
        if st.button("Salvar de-para deste cliente", type="primary"):
            salvar_linha_depara(cid, novo_analista, novo_setor, 1 if ativo else 0,
                                u["email"], grupo=str(linha.get("grupo", "") or ""))
            st.success("De-para salvo. Aplicado quando a carteira for recarregada.")

    dep_salvo = carregar_depara()
    if not dep_salvo.empty:
        st.markdown(f"**De-para salvo · {len(dep_salvo)} clientes**")
        # enriquece: mostra o analista EFETIVO (o da base quando o de-para está vazio)
        tabela = dep_salvo.copy()
        tabela["id_cliente"] = tabela["id_cliente"].astype(str).str.strip()
        tabela = tabela.rename(columns={"analista": "analista_dep"})
        analista_base = base[["id", "analista"]].copy()
        analista_base["id"] = analista_base["id"].astype(str).str.strip()
        analista_base = analista_base.rename(columns={"analista": "analista_base"})
        tabela = tabela.merge(analista_base, left_on="id_cliente", right_on="id", how="left")
        # analista efetivo: o do de-para se preenchido, senão o da base
        dep_txt = tabela["analista_dep"].fillna("").astype(str).str.strip()
        dep_vazio = dep_txt.str.lower().isin(["", "none", "nan", "null"])
        tabela["analista"] = tabela["analista_base"].where(dep_vazio, tabela["analista_dep"])
        tabela = tabela[["id_cliente", "grupo", "analista", "setor_gerencial", "ativo"]]
        st.dataframe(tabela, width="stretch", hide_index=True)

# --- abas ainda em construção ---
# --- Tabelas de Rating (aba 4) ---
with abas[4]:
    from src.raiox_abas import table_b2_ou_pior, table_top_bucket
    st.markdown("##### Tabelas por faixa de rating")
    for faixa in BUCKET_ORDER:
        t = table_top_bucket(base, faixa)
        if not t.empty:
            st.markdown(f"**Top 10 por limite · {faixa}**")
            st.dataframe(estilizar(t), width="stretch", hide_index=True)
    t_b2 = table_b2_ou_pior(base)
    if not t_b2.empty:
        st.markdown("**Top 10 por risco · B2 ou pior**")
        st.dataframe(estilizar(t_b2), width="stretch", hide_index=True)

# --- Movimentações (aba 5) ---
with abas[5]:
    from src.raiox_abas import (
        movement_available,
        table_movement,
        table_rating_movement,
    )
    st.markdown("##### Movimentações do mês")
    if not movement_available(base):
        st.info("A base carregada não tem colunas de comparação com o mês anterior "
                "(delta de limite, risco e rating). As movimentações aparecem quando "
                "a planilha traz esses dados de M-1.")
    else:
        blocos = [
            ("Aumento de limite · Top 10", table_movement(base, "limite", "up")),
            ("Redução de limite · Top 10", table_movement(base, "limite", "down")),
            ("Aumento de risco · Top 10", table_movement(base, "risco", "up")),
            ("Redução de risco · Top 10", table_movement(base, "risco", "down")),
            ("Upgrades de rating", table_rating_movement(base, "upgrade")),
            ("Downgrades de rating", table_rating_movement(base, "downgrade")),
        ]
        for titulo, tb in blocos:
            st.markdown(f"**{titulo}**")
            if tb.empty:
                st.caption("Nenhum registro nesta categoria.")
            else:
                st.dataframe(estilizar(tb), width="stretch", hide_index=True)

# --- Próximos Vencimentos (aba 6) ---
with abas[6]:
    import plotly.express as _px

    from src.raiox_abas import tabela_vencimentos
    st.markdown("##### Próximos vencimentos de limite")
    venc = tabela_vencimentos(base)
    if venc.empty:
        st.info("A base carregada não tem a data de vencimento de limite, ou "
                "nenhuma data válida foi encontrada.")
    else:
        meses = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
                 7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}
        venc = venc.copy()
        venc["Período"] = venc["Mês"].map(meses) + "/" + venc["Ano"].astype(str)
        fig = _px.bar(venc, x="Período", y="Risco (R$ mm)",
                      hover_data=["Grupos"], labels={"Risco (R$ mm)": "Risco (R$ mm)"},
                      color_discrete_sequence=["#14573A"])
        st.plotly_chart(fig, width="stretch")
        st.dataframe(venc[["Ano", "Mês", "Grupos", "Risco (R$ mm)"]],
                     width="stretch", hide_index=True)

# --- Visitas (aba 7) ---
with abas[7]:
    from src.raiox_abas import cobertura_visitas
    st.markdown("##### Cobertura de visitas por analista")
    vis = cobertura_visitas(base)
    if vis.empty:
        st.info("A base carregada não tem data de visita (ou não tem analista), "
                "então não dá para medir a cobertura de visitas.")
    else:
        st.dataframe(estilizar(vis), width="stretch", hide_index=True)
        import plotly.express as _px2
        fig = _px2.bar(vis, x="Analista", y=["Com visita", "Sem visita"],
                       barmode="stack", labels={"value": "Clientes", "variable": ""},
                       color_discrete_sequence=["#14573A", "#C6881C"])
        st.plotly_chart(fig, width="stretch")

# --- Clientes (aba 8) ---
with abas[8]:
    from src.raiox_abas import clientes_por_analista
    st.markdown("##### Clientes por analista")
    resumo_cli = clientes_por_analista(base)
    if resumo_cli.empty:
        st.info("A base carregada não tem a coluna de analista.")
    else:
        st.dataframe(estilizar(resumo_cli), width="stretch", hide_index=True)
        st.markdown("**Ver clientes de um analista**")
        analista_sel = st.selectbox("Analista", resumo_cli["Analista"].tolist(),
                                    key="cli_analista")
        det = base[base["analista"].astype(str) == str(analista_sel)].copy()
        det = det.sort_values("risco", ascending=False)
        cols = [c for c in ["id", "grupo", "setor_gerencial", "rating",
                            "limite", "risco", "disponibilidade", "data_visita",
                            "status", "comentario"] if c in det.columns]
        mostra = det[cols].rename(columns={
            "id": "ID", "grupo": "Grupo", "setor_gerencial": "Setor",
            "rating": "Rating", "limite": "Limite", "risco": "Risco",
            "disponibilidade": "Disponível", "data_visita": "Data visita",
            "status": "Status", "comentario": "Comentário"})
        st.dataframe(mostra, width="stretch", hide_index=True)

# --- Qualidade (aba 9) ---
with abas[9]:
    from src.raiox_abas import build_qualidade
    st.markdown("##### Qualidade / Pendências")
    resumo_q, detalhes_q = build_qualidade(base)
    if resumo_q.empty:
        st.info("Nenhuma checagem de qualidade disponível para esta base.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tipos de pendência", f"{int((resumo_q['Qtd'] > 0).sum())}")
        c2.metric("Ocorrências", f"{int(resumo_q['Qtd'].sum())}")
        c3.metric("Risco envolvido", _fmt_mm(resumo_q['Risco (R$ mm)'].sum() * 1_000_000))
        st.dataframe(estilizar(resumo_q), width="stretch", hide_index=True)
        st.markdown("**Ver clientes de uma pendência**")
        pend = st.selectbox("Pendência", resumo_q["Pendência"].tolist(), key="q_pend")
        det = detalhes_q.get(pend, None)
        if det is not None and not det.empty:
            st.dataframe(det.rename(columns={
                "id": "ID", "grupo": "Grupo", "analista": "Analista",
                "setor_gerencial": "Setor", "rating": "Rating",
                "limite": "Limite", "risco": "Risco", "data_visita": "Data visita"}),
                width="stretch", hide_index=True)
        else:
            st.caption("Nenhum cliente nesta pendência.")

# --- Comparação M-1 (aba 10) ---
with abas[10]:
    from src.raiox_abas import movement_available
    st.markdown("##### Comparação com o mês anterior (M-1)")
    if not movement_available(base):
        st.info("A base carregada não traz as colunas de M-1 (limite, risco e "
                "rating do mês anterior). Quando a planilha tiver esses dados, "
                "esta aba mostra a evolução automaticamente.")
    else:
        lim_atual = base["limite"].sum()
        lim_ant = base["limite_m1"].sum() if "limite_m1" in base.columns else 0
        ris_atual = base["risco"].sum()
        ris_ant = base["risco_m1"].sum() if "risco_m1" in base.columns else 0
        c1, c2 = st.columns(2)
        c1.metric("Limite total", _fmt_mm(lim_atual),
                  _fmt_mm(lim_atual - lim_ant), delta_color="normal")
        c2.metric("Risco total", _fmt_mm(ris_atual),
                  _fmt_mm(ris_atual - ris_ant), delta_color="inverse")
        # quem mais mudou
        st.markdown("**Maiores variações de risco no mês**")
        if "delta_risco" in base.columns:
            var = base[["grupo", "rating", "delta_risco", "risco"]].copy()
            var = var[var["delta_risco"].abs() > 0].sort_values(
                "delta_risco", key=abs, ascending=False).head(15)
            var["delta_risco"] = var["delta_risco"] / 1_000_000
            var["risco"] = var["risco"] / 1_000_000
            st.dataframe(var.rename(columns={
                "grupo": "Grupo", "rating": "Rating",
                "delta_risco": "Δ Risco (R$ mm)", "risco": "Risco (R$ mm)"}),
                width="stretch", hide_index=True)

# --- Exportar (aba 11) ---
with abas[11]:
    import io as _io
    st.markdown("##### Exportar a carteira")
    st.caption("Baixe a carteira atual (com de-para e comentários já aplicados) "
               "em Excel, para guardar ou compartilhar.")
    buf = _io.BytesIO()
    cols_exp = [c for c in ["id", "grupo", "analista", "setor_gerencial", "rating",
                            "bucket_rating", "limite", "risco", "disponibilidade",
                            "data_visita", "status", "comentario"] if c in base.columns]
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        base[cols_exp].to_excel(writer, index=False, sheet_name="Carteira")
    st.download_button(
        "📥 Baixar carteira em Excel",
        data=buf.getvalue(),
        file_name="carteira_raio_x.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    st.caption("A exportação em PDF (relatório formatado) pode ser adicionada "
               "numa próxima fase.")
