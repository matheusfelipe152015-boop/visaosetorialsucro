"""Raio X — núcleo de dados da carteira de crédito.

Privacidade (regra de ouro do Matheus): a carteira NUNCA é salva. Ela é lida do
Excel enviado, normalizada e usada só na sessão. O único dado que persiste é o
comentário/status por cliente (ligado ao ID), guardado no banco.

Este módulo tem:
  · o mapa de colunas e ratings (fiel ao app original do Raio X);
  · normalize_base(): padroniza qualquer planilha de carteira;
  · cálculo de PD média e rating médio;
  · leitura/gravação dos comentários por ID.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy import text

from src.persistence.db import _fetch_df_raw, get_engine

# ── ratings (fiel ao Raio X) ──────────────────────────────────────────────

RATING_LABEL_TO_NUM = {
    "AAA": 1, "AA1": 1, "AA2": 1, "AA3": 1,
    "A1": 1, "A2": 1, "A3": 1, "A4": 1,
    "BAA1": 2, "BAA2": 2,
    "BAA3": 3, "BAA4": 3,
    "BA1": 4, "BA2": 4,
    "BA3": 5, "BA4": 5,
    "BA5": 6, "BA6": 6,
    "B1": 7,
    "B2": 8, "B3": 8,
    "B4": 9,
    "C1": 10,
    "C2": 11, "C3": 11,
    "D1": 13, "D2": 13,
    "D3": 14, "D4": 14,
    "EA1": 15, "E1": 15,
    "EA2": 16, "E2": 16,
    "EA3": 17, "E3": 17,
    "F1": 18, "F2": 18,
    "F3": 19,
    "G1": 20,
    "G2": 21,
    "H": 22,
    "P": 23,
}

RATING_NUM_TO_LABEL = {
    1: "A1", 2: "Baa1", 3: "Baa4", 4: "Ba1", 5: "Ba4", 6: "Ba6",
    7: "B1", 8: "B2", 9: "B4", 10: "C1", 11: "C2", 12: "C3",
    13: "D1", 14: "D3", 15: "Ea1", 16: "Ea2", 17: "Ea3", 18: "F1",
    19: "F3", 20: "G1", 21: "G2", 22: "H", 23: "P",
}

# PD de 12 meses por rótulo (para PD média ponderada pelo risco)
PD_AGRO_RATING = {
    "AAA": 0.000408909, "AA1": 0.000408909, "AA2": 0.000408909, "AA3": 0.000408909,
    "A1": 0.000408909, "A2": 0.000408909, "A3": 0.000408909, "A4": 0.000408909,
    "BAA1": 0.000758091, "BAA2": 0.000758091,
    "BAA3": 0.001405032, "BAA4": 0.001405032,
    "BA1": 0.002800421, "BA2": 0.002800421,
    "BA3": 0.004816066, "BA4": 0.004816066,
    "BA5": 0.008895182, "BA6": 0.008895182,
    "B1": 0.025919544,
    "B2": 0.029944974, "B3": 0.029944974,
    "B4": 0.070281960,
    "C1": 0.144562854,
    "C2": 0.1792, "C3": 0.1792,
    "D1": 0.267498231, "D2": 0.267498231,
    "D3": 0.406593407, "D4": 0.406593407,
    "EA1": 1.0, "E1": 1.0, "EA2": 1.0, "E2": 1.0, "EA3": 1.0, "E3": 1.0,
    "F1": 1.0, "F2": 1.0, "F3": 1.0, "G1": 1.0, "G2": 1.0, "H": 1.0, "P": 1.0,
}

PD_RATING_CUTS = [
    ("A1", 0.000408909), ("Baa1", 0.000758091), ("Baa4", 0.001405032),
    ("Ba1", 0.002800421), ("Ba4", 0.004816066), ("Ba6", 0.008895182),
    ("B1", 0.025919544), ("B2", 0.029944974), ("B4", 0.070281960),
    ("C1", 0.144562854), ("C2", 0.1792), ("D1", 0.267498231),
    ("D3", 0.406593407), ("E's - H", 1.0),
]

# mapeamento flexível de colunas (a planilha pode ter nomes variados)
COLUMN_OPTIONS = {
    "id": ["ID", "idGrupo", "id_grupo_cliente"],
    "grupo": ["Nome do grupo", "nomeGrupo", "nm_grupo_cliente", "nomegrupo",
              "des_grupo_consolidado", "grupo"],
    "analista": ["Analista Podicre", "analista", "Analista 2026", "analistaEsg"],
    "setor_gerencial": ["Agrupamento Setor Gerencial", "setorGerencialPodicre",
                        "setor", "nm_setor_gerencial", "setor_gerencial"],
    "limite": ["Limite mês Atual Podicre", "valorLimite", "vl_limite_credito", "Limite",
               "limite"],
    "risco": ["Risco Mês Atual Podicre", "valorRisco", "Sum of vl_risco_credito",
              "Risco", "val_risco_itau", "risco"],
    "disponibilidade": ["Disponibilidade", "valorLimiteDisponivel", "disponibilidade"],
    "rating": ["Rating Mês Atual Podicre", "rating", "Rating", "des_rating_consolidado"],
    "rating_num": ["Nº Rating Mês Atual Podicre", "Número Rating"],
    "limite_m1": ["Limite mês Anterior Podicre"],
    "risco_m1": ["Risco Mês Anterior Podicre"],
    "rating_m1": ["Rating Mês Anterior Podicre"],
    "rating_num_m1": ["Nº Rating Mês anterior Podicre"],
    "data_venc_limite": ["dataVencLimite", "dt_vto_lim_credito", "Venc limite"],
    "data_venc_rating": ["Vencimento de rating atual", "dataVencRatingAtual",
                         "dt_vencimento_rating", "Venc rating"],
    "data_visita": ["DataVisita", "dataVisita", "DATA_VISITA", "Data Visita",
                    "UltimaVisita", "Última Visita", "data_visita"],
    "gerente_oficial": ["Gerente", "gerente", "gerente_oficial"],
    "officer": ["officer", "Officer", "Officer Podicre", "officerPodicre"],
    "diretor_comercial": ["diretorComercial", "Diretor Comercial", "diretor_comercial",
                          "diretorComercialPodicre"],
    "des_farol": ["Des_Farol", "des_farol", "Farol", "farol"],
    "elegibilidade": ["elegibilidade", "Elegibilidade", "Elegibilidade Renovação"],
}

BUCKET_ORDER = ["A1 - Baa4", "Ba1 - Ba4", "Ba6 ou pior"]


def _find_col(df: pd.DataFrame, names: list[str]) -> str | None:
    low = {str(c).strip().lower(): c for c in df.columns}
    for name in names:
        c = low.get(str(name).strip().lower())
        if c is not None:
            return c
    return None


def _bucket(n) -> str:
    if pd.isna(n):
        return "Não classificado"
    n = int(n)
    if 1 <= n <= 3:
        return "A1 - Baa4"
    if 4 <= n <= 5:
        return "Ba1 - Ba4"
    if n >= 6:
        return "Ba6 ou pior"
    return "Não classificado"


def garantir_escala(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza os valores em REAIS.

    Planilhas do banco costumam vir com os valores JÁ em milhões (limite 4.116
    = R$ 4,1 bi). Se a mediana do limite for pequena demais para ser reais,
    assume MM e converte. Idempotente: rodar duas vezes não muda nada.
    """
    if "limite" not in df.columns:
        return df
    out = df.copy()
    mediana = pd.to_numeric(out["limite"], errors="coerce").median()
    if pd.notna(mediana) and 0 < mediana < 100_000:
        for c in ["limite", "risco", "disponibilidade", "limite_m1", "risco_m1"]:
            if c in out.columns:
                out[c] = pd.to_numeric(out[c], errors="coerce") * 1_000_000
    return out


def ler_carteira_excel(arquivo) -> pd.DataFrame:
    """Lê a planilha detectando automaticamente a linha do cabeçalho.

    A planilha pode ter o cabeçalho na primeira linha (mais comum) ou na linha 8
    (padrão antigo do Raio X). Testamos as posições e usamos a que reconhecer as
    colunas conhecidas (grupo, risco, rating...).
    """
    xls = pd.ExcelFile(arquivo, engine="openpyxl")
    sheet = xls.sheet_names[0]
    # colunas-chave que indicam que achamos o cabeçalho certo
    sinais = []
    for opts in COLUMN_OPTIONS.values():
        sinais.extend(str(o).strip().lower() for o in opts)

    melhor = None
    melhor_pontos = -1
    for header in (0, 7, 1, 2):
        try:
            df = pd.read_excel(arquivo, sheet_name=sheet, engine="openpyxl", header=header)
        except Exception:  # noqa: BLE001
            continue
        cols = {str(c).strip().lower() for c in df.columns}
        pontos = len(cols & set(sinais))
        if pontos > melhor_pontos and df.shape[1] >= 3:
            melhor_pontos = pontos
            melhor = df
    if melhor is None or melhor_pontos == 0:
        # nenhuma posição reconheceu colunas: devolve a leitura padrão para o
        # erro aparecer de forma clara em normalize_base
        return pd.read_excel(arquivo, sheet_name=sheet, engine="openpyxl")
    return melhor


def normalize_base(df: pd.DataFrame) -> pd.DataFrame:
    """Padroniza uma planilha de carteira para as colunas internas do Raio X."""
    out = df.copy()
    colmap = {key: _find_col(out, opts) for key, opts in COLUMN_OPTIONS.items()}

    new = pd.DataFrame(index=out.index)
    for key, col in colmap.items():
        if col is not None:
            new[key] = out[col]

    # renovação automática: aceita qualquer coluna cujo nome contenha "renov"
    if "renovacao_automatica" not in new.columns:
        for c in out.columns:
            if "renov" in str(c).strip().lower():
                new["renovacao_automatica"] = out[c]
                break

    if "grupo" not in new.columns:
        raise ValueError("Não encontrei a coluna de grupo na base carregada.")
    if "id" not in new.columns:
        new["id"] = range(1, len(new) + 1)
    new["id"] = new["id"].astype(str).str.strip()

    for c in ["limite", "risco", "disponibilidade", "limite_m1", "risco_m1",
              "rating_num", "rating_num_m1"]:
        if c in new.columns:
            new[c] = pd.to_numeric(new[c], errors="coerce")

    new = garantir_escala(new)

    # rating textual -> numérico
    if "rating_num" not in new.columns or new["rating_num"].isna().all():
        if "rating" in new.columns:
            new["rating"] = new["rating"].astype(str).str.strip().str.upper()
            new["rating_num"] = new["rating"].map(RATING_LABEL_TO_NUM)
    elif "rating" not in new.columns:
        new["rating"] = new["rating_num"].map(RATING_NUM_TO_LABEL)

    # rating anterior (M-1)
    if ("rating_num_m1" not in new.columns or new["rating_num_m1"].isna().all()) \
            and "rating_m1" in new.columns:
        new["rating_m1"] = new["rating_m1"].astype(str).str.strip().str.upper()
        new["rating_num_m1"] = new["rating_m1"].map(RATING_LABEL_TO_NUM)

    # deltas
    if {"limite", "limite_m1"}.issubset(new.columns):
        new["delta_limite"] = new["limite"] - new["limite_m1"]
    if {"risco", "risco_m1"}.issubset(new.columns):
        new["delta_risco"] = new["risco"] - new["risco_m1"]
    if {"rating_num", "rating_num_m1"}.issubset(new.columns):
        new["delta_rating"] = new["rating_num_m1"] - new["rating_num"]

    # preenchimentos
    if "limite" not in new.columns:
        new["limite"] = 0.0
    if "risco" not in new.columns:
        new["risco"] = 0.0
    if "disponibilidade" not in new.columns:
        new["disponibilidade"] = new["limite"] - new["risco"]
    for c, padrao in [("setor_gerencial", "Não informado"),
                      ("analista", "Não informado"),
                      ("gerente_oficial", "Não informado"),
                      ("des_farol", "")]:
        if c not in new.columns:
            new[c] = padrao

    if "data_visita" not in new.columns:
        new["data_visita"] = pd.NaT
    new["data_visita"] = pd.to_datetime(new["data_visita"], errors="coerce", dayfirst=True)

    if "rating_num" in new.columns:
        new["bucket_rating"] = new["rating_num"].apply(_bucket)
    else:
        new["bucket_rating"] = "Não classificado"
    # risco/limite: nunca divide por zero (limite 0 vira NA -> resultado NA)
    limite_seguro = new["limite"].replace({0: pd.NA})
    new["rl"] = new["risco"] / limite_seguro

    new["grupo"] = new["grupo"].astype(str).str.strip()
    new["setor_gerencial"] = new["setor_gerencial"].fillna("Não informado").astype(str)
    new["analista"] = new["analista"].fillna("Não informado").astype(str)
    if "rating" in new.columns:
        new["rating"] = new["rating"].fillna(
            new["rating_num"].map(RATING_NUM_TO_LABEL) if "rating_num" in new.columns else ""
        ).astype(str)

    return new


def calcular_pd_e_rating_medio(df: pd.DataFrame) -> tuple[float | None, str]:
    """PD média ponderada pelo risco + rating médio correspondente."""
    if df is None or df.empty or "risco" not in df.columns or "rating" not in df.columns:
        return None, "-"
    base = df.copy()
    base["risco"] = pd.to_numeric(base["risco"], errors="coerce").fillna(0)
    base["rating_norm"] = base["rating"].astype(str).str.strip().str.upper()
    base["pd_rating"] = base["rating_norm"].map(PD_AGRO_RATING)
    base = base[(base["risco"] > 0) & (base["pd_rating"].notna())].copy()
    if base.empty:
        return None, "-"
    risco_total = base["risco"].sum()
    if risco_total == 0:
        return None, "-"
    pd_media = (base["risco"] * base["pd_rating"]).sum() / risco_total
    rating_medio = "E's - H"
    for rating_label, pd_corte in PD_RATING_CUTS:
        if pd_media <= pd_corte:
            rating_medio = rating_label
            break
    return pd_media, rating_medio


# ── comentários por ID (o único dado que persiste) ────────────────────────

def carregar_comentarios() -> pd.DataFrame:
    """Lê os comentários salvos (sem cache: refletem na hora)."""
    return _fetch_df_raw(
        "SELECT id_cliente, status, comentario FROM raiox_comentarios"
    )


def aplicar_comentarios(base: pd.DataFrame) -> pd.DataFrame:
    """Junta os comentários salvos à carteira em memória, casando pelo ID."""
    out = base.copy()
    out["id"] = out["id"].astype(str).str.strip()
    coment = carregar_comentarios()
    if coment.empty:
        out["status"] = ""
        out["comentario"] = ""
        return out
    coment["id_cliente"] = coment["id_cliente"].astype(str).str.strip()
    out = out.merge(coment, left_on="id", right_on="id_cliente", how="left")
    out["status"] = out["status"].fillna("")
    out["comentario"] = out["comentario"].fillna("")
    if "id_cliente" in out.columns:
        out = out.drop(columns=["id_cliente"])
    return out


def salvar_comentario(id_cliente: str, status: str, comentario: str,
                      quem: str = "") -> None:
    """Grava (ou atualiza) o comentário de um cliente pelo ID."""
    id_cliente = str(id_cliente).strip()
    agora = datetime.utcnow()
    with get_engine().begin() as conn:
        existe = conn.execute(
            text("SELECT id_cliente FROM raiox_comentarios WHERE id_cliente = :i"),
            {"i": id_cliente},
        ).first()
        if existe:
            conn.execute(
                text("""UPDATE raiox_comentarios
                        SET status = :s, comentario = :c,
                            atualizado_em = :a, atualizado_por = :q
                        WHERE id_cliente = :i"""),
                {"i": id_cliente, "s": status, "c": comentario, "a": agora, "q": quem},
            )
        else:
            conn.execute(
                text("""INSERT INTO raiox_comentarios
                        (id_cliente, status, comentario, atualizado_em, atualizado_por)
                        VALUES(:i, :s, :c, :a, :q)"""),
                {"i": id_cliente, "s": status, "c": comentario, "a": agora, "q": quem},
            )


# ── base de TESTE (só dados fictícios) ────────────────────────────────────
# Guarda uma carteira inteira no banco — o que normalmente é proibido. Existe
# só para testes com dados fictícios; a tela sempre avisa disso.

def salvar_base_teste(df: pd.DataFrame, quem: str = "") -> None:
    """Salva a carteira (fictícia) como base de teste. Substitui a anterior."""
    dados = df.to_json(orient="records", date_format="iso")
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM raiox_base_teste"))  # só uma base por vez
        conn.execute(
            text("""INSERT INTO raiox_base_teste(id, dados_json, linhas, salvo_em, salvo_por)
                    VALUES(:id, :d, :n, :s, :q)"""),
            {"id": uuid.uuid4().hex, "d": dados, "n": len(df),
             "s": datetime.utcnow(), "q": quem},
        )


def carregar_base_teste() -> pd.DataFrame | None:
    """Carrega a base de teste salva (ou None se não houver)."""
    df = _fetch_df_raw("SELECT dados_json FROM raiox_base_teste LIMIT 1")
    if df.empty:
        return None
    import io
    out = pd.read_json(io.StringIO(df.iloc[0]["dados_json"]), orient="records")
    if "id" in out.columns:
        out["id"] = out["id"].astype(str).str.strip()
    return garantir_escala(out)


def existe_base_teste() -> bool:
    df = _fetch_df_raw("SELECT id FROM raiox_base_teste LIMIT 1")
    return not df.empty


def excluir_base_teste() -> None:
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM raiox_base_teste"))
