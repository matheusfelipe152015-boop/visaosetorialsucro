"""De-para editável — mapa de cliente -> analista, setor gerencial, ativo/inativo.

Ao contrário da carteira (que nunca é salva), o de-para FICA salvo no banco: é só
configuração, sem dado sensível. Fluxo:
  · sobe uma planilha de de-para -> importa para o banco (por ID);
  · edita no app (analista, setor, ativo/inativo) -> salva no banco;
  · quando a carteira é carregada, o de-para é aplicado por cima (casando por ID):
    sobrescreve analista/setor e remove os clientes marcados como inativos.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
from sqlalchemy import text

from src.persistence.db import _fetch_df_raw, get_engine
from src.raiox import _find_col


def _sim_nao_para_int(v) -> int:
    """Interpreta 'ativo': texto/again vira 1 (ativo) ou 0 (inativo)."""
    s = str(v).strip().lower()
    if s in ("não", "nao", "n", "0", "inativo", "false", "no"):
        return 0
    return 1


def importar_depara_excel(arquivo, quem: str = "") -> tuple[int, str]:
    """Lê uma planilha de de-para e grava no banco (por ID). (linhas, msg)."""
    try:
        xls = pd.ExcelFile(arquivo, engine="openpyxl")
        dep = pd.read_excel(arquivo, sheet_name=xls.sheet_names[0], engine="openpyxl")
    except Exception as exc:  # noqa: BLE001
        return 0, f"Não consegui ler a planilha: {exc}"

    id_col = _find_col(dep, ["ID", "idGrupo", "id_grupo_cliente", "id"])
    if id_col is None:
        return 0, "Não encontrei a coluna de ID na planilha de de-para."

    analista_col = _find_col(dep, ["Analista", "analista", "Analista 2026", "Analista Podicre"])
    setor_col = _find_col(dep, ["recorte_gerencial", "Setor", "setor",
                                "Agrupamento Setor Gerencial", "setorGerencialPodicre"])
    grupo_col = _find_col(dep, ["nome_grupo", "Nome do grupo", "nomeGrupo", "Grupo"])
    ativo_col = _find_col(dep, ["Ativo", "ativo"])

    agora = datetime.utcnow()
    linhas = 0
    with get_engine().begin() as conn:
        for _, r in dep.iterrows():
            cid = str(r[id_col]).strip()
            if not cid or cid.lower() == "nan":
                continue
            grupo = str(r[grupo_col]).strip() if grupo_col else None
            analista = str(r[analista_col]).strip() if analista_col else None
            setor = str(r[setor_col]).strip() if setor_col else None
            ativo = _sim_nao_para_int(r[ativo_col]) if ativo_col else 1
            _upsert(conn, cid, grupo, analista, setor, ativo, agora, quem)
            linhas += 1
    return linhas, f"De-para importado: {linhas} clientes."


def _upsert(conn, cid, grupo, analista, setor, ativo, agora, quem):
    existe = conn.execute(
        text("SELECT id_cliente FROM depara WHERE id_cliente = :i"), {"i": cid}
    ).first()
    dados = {"i": cid, "g": grupo, "a": analista, "s": setor,
             "at": ativo, "up": agora, "por": quem}
    if existe:
        conn.execute(
            text("""UPDATE depara SET grupo=:g, analista=:a, setor_gerencial=:s,
                    ativo=:at, atualizado_em=:up, atualizado_por=:por
                    WHERE id_cliente=:i"""), dados)
    else:
        conn.execute(
            text("""INSERT INTO depara
                    (id_cliente, grupo, analista, setor_gerencial, ativo,
                     atualizado_em, atualizado_por)
                    VALUES(:i,:g,:a,:s,:at,:up,:por)"""), dados)


def carregar_depara() -> pd.DataFrame:
    """Lê o de-para salvo (sem cache)."""
    return _fetch_df_raw(
        "SELECT id_cliente, grupo, analista, setor_gerencial, ativo FROM depara"
    )


def salvar_linha_depara(id_cliente: str, analista: str, setor: str,
                        ativo: int, quem: str = "", grupo: str | None = None) -> None:
    """Salva/atualiza uma linha do de-para (edição no app)."""
    with get_engine().begin() as conn:
        _upsert(conn, str(id_cliente).strip(), grupo, analista, setor,
                int(ativo), datetime.utcnow(), quem)


def _valor_real(serie: pd.Series) -> pd.Series:
    """Marca como NaN os 'vazios disfarçados' (None, '', 'nan', 'none')."""
    limpa = serie.fillna("").astype(str).str.strip()
    vazio = limpa.str.lower().isin(["", "none", "nan", "null"])
    return serie.where(~vazio)


def aplicar_depara(base: pd.DataFrame) -> pd.DataFrame:
    """Aplica o de-para salvo por cima da carteira (casando por ID).

    Regra: a BASE manda. O de-para só sobrescreve analista/setor quando tem um
    valor de verdade preenchido (edição consciente). Vazio no de-para = mantém o
    que veio da base. Além disso, remove os clientes marcados como inativos.
    """
    dep = carregar_depara()
    if dep.empty:
        return base
    out = base.copy()
    out["id"] = out["id"].astype(str).str.strip()
    dep["id_cliente"] = dep["id_cliente"].astype(str).str.strip()

    out = out.merge(dep, left_on="id", right_on="id_cliente", how="left",
                    suffixes=("", "_dep"))

    # sobrescreve SÓ quando o de-para tem valor real (senão mantém o da base)
    if "analista_dep" in out.columns:
        out["analista"] = _valor_real(out["analista_dep"]).combine_first(out["analista"])
    if "setor_gerencial_dep" in out.columns:
        out["setor_gerencial"] = _valor_real(out["setor_gerencial_dep"]).combine_first(
            out["setor_gerencial"])

    # remove inativos (ativo == 0 no de-para)
    if "ativo" in out.columns:
        out = out[out["ativo"].fillna(1) != 0].copy()

    # limpa colunas auxiliares do merge
    aux = [c for c in out.columns
           if c.endswith("_dep") or c in ("id_cliente", "ativo", "grupo_dep")]
    out = out.drop(columns=[c for c in aux if c in out.columns])
    return out
