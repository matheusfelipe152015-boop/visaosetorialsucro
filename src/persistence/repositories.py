"""Repositórios: upsert idempotente e registro de execuções.

O upsert usa ON CONFLICT (suportado por SQLite >=3.24 e PostgreSQL), de modo
que reexecutar uma coleta nunca duplica registros.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text

from src.domain.models import CollectorResult, IndicatorValue

from .db import get_engine

_UPSERT_VALUE = text(
    """
    INSERT INTO indicator_values
        (id, indicator_code, source_code, data_referencia, data_publicacao,
         data_coleta, valor, unidade, moeda, escala, hash, collector_version,
         status_validacao, url_original)
    VALUES
        (:id, :indicator_code, :source_code, :data_referencia, :data_publicacao,
         :data_coleta, :valor, :unidade, :moeda, :escala, :hash, :collector_version,
         :status_validacao, :url_original)
    ON CONFLICT (indicator_code, data_referencia, source_code)
    DO UPDATE SET valor = excluded.valor,
                  data_coleta = excluded.data_coleta,
                  hash = excluded.hash,
                  status_validacao = excluded.status_validacao
    """
)


def upsert_indicator_values(values: list[IndicatorValue]) -> int:
    """Insere/atualiza e devolve quantos registros eram novos (insert)."""
    eng = get_engine()
    new = 0
    with eng.begin() as conn:
        for v in values:
            exists = conn.execute(
                text(
                    "SELECT 1 FROM indicator_values "
                    "WHERE indicator_code=:i AND data_referencia=:d AND source_code=:s"
                ),
                {"i": v.indicator_code, "d": v.data_referencia, "s": v.source_code},
            ).first()
            if not exists:
                new += 1
            conn.execute(
                _UPSERT_VALUE,
                {
                    "id": uuid.uuid4().hex,
                    "indicator_code": v.indicator_code,
                    "source_code": v.source_code,
                    "data_referencia": v.data_referencia,
                    "data_publicacao": v.data_publicacao,
                    "data_coleta": v.data_coleta,
                    "valor": v.valor,
                    "unidade": v.unidade,
                    "moeda": v.moeda,
                    "escala": v.escala,
                    "hash": v.hash,
                    "collector_version": v.collector_version,
                    "status_validacao": str(v.status_validacao),
                    "url_original": v.url_original,
                },
            )
    return new


def log_run(result: CollectorResult) -> None:
    """Registra a execução. À prova de falha: nunca derruba a rotina de coleta.

    Garante que a fonte exista (cadastro mínimo) antes de anotar o evento, e
    engole qualquer erro de log — registrar saúde jamais pode quebrar o job.
    """
    try:
        with get_engine().begin() as conn:
            # garante que a fonte exista (evita erro de chave estrangeira em banco novo)
            conn.execute(
                text(
                    "INSERT INTO sources (code, nome) VALUES (:s, :s) "
                    "ON CONFLICT (code) DO NOTHING"
                ),
                {"s": result.source_code},
            )
            conn.execute(
                text(
                    """INSERT INTO source_runs
                       (id, source_code, started_at, finished_at, rows_seen, rows_new,
                        ok, error, duration_s)
                       VALUES (:id,:s,:a,:b,:seen,:new,:ok,:err,:dur)"""
                ),
                {
                    "id": uuid.uuid4().hex,
                    "s": result.source_code,
                    "a": result.started_at,
                    "b": result.finished_at,
                    "seen": result.rows_seen,
                    "new": result.rows_new,
                    "ok": result.ok,
                    "err": result.error,
                    "dur": result.duration_s,
                },
            )
            # marca disponibilidade da fonte para a página de Saúde
            conn.execute(
                text("UPDATE sources SET available=:ok WHERE code=:s"),
                {"ok": result.ok, "s": result.source_code},
            )
    except Exception as exc:  # noqa: BLE001 — log de saúde nunca derruba o job
        print(f"  (aviso: não foi possível registrar a saúde de {result.source_code}: {exc})")


def upsert_company_metrics(rows: list[dict]) -> int:
    """Insere/atualiza métricas de empresa (operacional/financeiro), idempotente.

    Chave de unicidade: (company_code, metric, periodo, fonte). Devolve quantos
    registros eram novos. Cada row: company, metric, valor, unidade, grupo,
    periodo, fonte, data_referencia, data_publicacao (opcionais com default).
    """
    from datetime import datetime

    eng = get_engine()
    new = 0
    with eng.begin() as conn:
        for r in rows:
            periodo = r.get("periodo", "")
            fonte = r.get("fonte", "")
            exists = conn.execute(
                text(
                    "SELECT 1 FROM company_metrics "
                    "WHERE company_code=:c AND metric=:m AND periodo=:p AND fonte=:f"
                ),
                {"c": r["company"], "m": r["metric"], "p": periodo, "f": fonte},
            ).first()
            if not exists:
                new += 1
            conn.execute(
                text(
                    """INSERT INTO company_metrics
                       (id, company_code, metric, grupo, safra, periodo, data_referencia,
                        valor, unidade, fonte, data_publicacao, data_coleta,
                        collector_version, status_validacao, url_original)
                       VALUES (:id,:c,:m,:g,:sf,:p,:dr,:v,:u,:f,:dp,:dc,:cv,:st,:url)
                       ON CONFLICT (company_code, metric, periodo, fonte) DO UPDATE SET
                         valor=excluded.valor, data_referencia=excluded.data_referencia,
                         data_coleta=excluded.data_coleta,
                         status_validacao=excluded.status_validacao"""
                ),
                {
                    "id": uuid.uuid4().hex,
                    "c": r["company"],
                    "m": r["metric"],
                    "g": r.get("grupo", "financeiro"),
                    "sf": r.get("safra"),
                    "p": periodo,
                    "dr": r.get("data_referencia"),
                    "v": r["valor"],
                    "u": r.get("unidade"),
                    "f": fonte,
                    "dp": r.get("data_publicacao"),
                    "dc": datetime.utcnow(),
                    "cv": r.get("collector_version", "0.1.0"),
                    "st": r.get("status_validacao", "a_conferir"),
                    "url": r.get("url_original"),
                },
            )
    return new
