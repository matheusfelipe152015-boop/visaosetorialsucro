"""Bloco Etanol — coletores das séries do sugar-intel que têm tabela própria.

São dados sem indicador direto no catálogo (curva forward, base regional,
defasagem de paridade), por isso vão para tabelas dedicadas (migração 0016).
A aba Mercado lê dessas tabelas.

Atribuição: dados compilados pelo projeto sugar-intel (Igor Strongylis) a partir
de B3, CEPEA/ESALQ e ABICOM.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime

from sqlalchemy import text

from src.collectors.market.mercado_intel import SOURCE_CODE, _baixar, _data, _num, _rodar
from src.persistence.db import get_engine


def _linhas(arquivo: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(_baixar(arquivo))))


# ── B3 — curva forward do etanol hidratado ────────────────────────────────
class B3EtanolCollector:
    """Ajustes por vencimento (ETHc1, ETHc2, ETHc3...) — mantém histórico."""

    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        linhas = _linhas("b3_eth.csv")
        n = 0
        with get_engine().begin() as conn:
            for r in linhas:
                d = _data(r.get("data"))
                venc = (r.get("vencimento") or "").strip()
                if not d or not venc:
                    continue
                p = {"id": uuid.uuid4().hex, "d": d, "v": venc,
                     "aj": _num(r.get("ajuste")), "vol": _num(r.get("volume")),
                     "oi": _num(r.get("contratos_aberto")), "dc": datetime.utcnow()}
                existe = conn.execute(
                    text("SELECT 1 FROM b3_eth_curva WHERE vencimento=:v AND data_ref=:d"),
                    {"v": venc, "d": d}).first()
                if existe:
                    conn.execute(text("""UPDATE b3_eth_curva SET ajuste=:aj, volume=:vol,
                        contratos_aberto=:oi WHERE vencimento=:v AND data_ref=:d"""), p)
                else:
                    conn.execute(text("""INSERT INTO b3_eth_curva
                        (id,data_ref,vencimento,ajuste,volume,contratos_aberto,data_coleta)
                        VALUES(:id,:d,:v,:aj,:vol,:oi,:dc)"""), p)
                    n += 1
        return len(linhas), n

    def run(self):
        return _rodar("b3_eth", self._coletar)


# ── Base do hidratado: SP menos GO ────────────────────────────────────────
class BaseSpGoCollector:
    """Cruza o hidratado semanal de SP (CEPEA) com o de GO e grava a base."""

    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        sp = {}
        for r in _linhas("cepea_etanol_sp.csv"):
            d = _data(r.get("semana_inicio"))
            v = _num(r.get("preco_hidratado_r$_l"))
            if d and v is not None:
                sp[d] = v
        go = {}
        for r in _linhas("cepea_etanol_go.csv"):
            d = _data(r.get("semana_inicio"))
            v = _num(r.get("preco_interno_r$_l"))
            if d and v is not None:
                go[d] = v

        comuns = sorted(set(sp) & set(go))
        n = 0
        with get_engine().begin() as conn:
            for d in comuns:
                p = {"id": uuid.uuid4().hex, "d": d, "sp": sp[d], "go": go[d],
                     "base": round(sp[d] - go[d], 4), "dc": datetime.utcnow()}
                existe = conn.execute(
                    text("SELECT 1 FROM etanol_base_sp_go WHERE semana_inicio=:d"),
                    {"d": d}).first()
                if existe:
                    conn.execute(text("""UPDATE etanol_base_sp_go SET sp_rs_l=:sp,
                        go_rs_l=:go, base_rs_l=:base WHERE semana_inicio=:d"""), p)
                else:
                    conn.execute(text("""INSERT INTO etanol_base_sp_go
                        (id,semana_inicio,sp_rs_l,go_rs_l,base_rs_l,data_coleta)
                        VALUES(:id,:d,:sp,:go,:base,:dc)"""), p)
                    n += 1
        return len(comuns), n

    def run(self):
        return _rodar("base_sp_go", self._coletar)


# ── ABICOM — defasagem da paridade de importação ──────────────────────────
class AbicomPpiCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        linhas = _linhas("abicom_ppi.csv")
        n = 0
        with get_engine().begin() as conn:
            for r in linhas:
                d = _data(r.get("data"))
                if not d:
                    continue
                p = {"id": uuid.uuid4().hex, "d": d,
                     "di": _num(r.get("defasagem_diesel_pct")),
                     "ga": _num(r.get("defasagem_gasolina_pct")),
                     "ptax": _num(r.get("ptax_brl_usd")),
                     "brent": _num(r.get("brent_usd_bbl")), "dc": datetime.utcnow()}
                existe = conn.execute(text("SELECT 1 FROM abicom_ppi WHERE data_ref=:d"),
                                      {"d": d}).first()
                if existe:
                    conn.execute(text("""UPDATE abicom_ppi SET defasagem_diesel_pct=:di,
                        defasagem_gasolina_pct=:ga, ptax_brl_usd=:ptax,
                        brent_usd_bbl=:brent WHERE data_ref=:d"""), p)
                else:
                    conn.execute(text("""INSERT INTO abicom_ppi
                        (id,data_ref,defasagem_diesel_pct,defasagem_gasolina_pct,
                         ptax_brl_usd,brent_usd_bbl,data_coleta)
                        VALUES(:id,:d,:di,:ga,:ptax,:brent,:dc)"""), p)
                    n += 1
        return len(linhas), n

    def run(self):
        return _rodar("abicom", self._coletar)


COLETORES_ETANOL = [B3EtanolCollector, BaseSpGoCollector, AbicomPpiCollector]


# ── UNICA — oferta × demanda mensal (formato largo → longo) ───────────────
_MESES_SAFRA = {"Abr": 4, "Mai": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Set": 9,
                "Out": 10, "Nov": 11, "Dez": 12, "Jan": 1, "Fev": 2, "Mar": 3}


def _data_do_mes(safra: str, mes_nome: str):
    """'25/26' + 'Abr' -> 2025-04-01 ; '25/26' + 'Jan' -> 2026-01-01."""
    from datetime import date as _date
    partes = str(safra or "").split("/")
    if len(partes) != 2 or not partes[0].strip().isdigit():
        return None
    ano1 = 2000 + int(partes[0].strip())
    mes = _MESES_SAFRA.get(mes_nome)
    if not mes:
        return None
    ano = ano1 if mes >= 4 else ano1 + 1
    return _date(ano, mes, 1)


class UnicaSndCollector:
    """Séries mensais da UNICA: entradas, saídas, estoque, moagem, mix, chuva."""

    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        linhas = _linhas("unica_snd.csv")
        registros = []
        for r in linhas:
            serie = (r.get("serie") or "").strip()
            safra = (r.get("safra") or "").strip()
            if not serie or not safra:
                continue
            for mes_nome in _MESES_SAFRA:
                v = _num(r.get(mes_nome))
                d = _data_do_mes(safra, mes_nome)
                if v is None or d is None:
                    continue
                registros.append({"serie": serie, "safra": safra, "d": d, "v": v})

        n = 0
        with get_engine().begin() as conn:
            for x in registros:
                p = {"id": uuid.uuid4().hex, **x, "dc": datetime.utcnow()}
                existe = conn.execute(
                    text("SELECT 1 FROM unica_snd WHERE serie=:serie AND safra=:safra "
                         "AND data_ref=:d"),
                    {"serie": x["serie"], "safra": x["safra"], "d": x["d"]}).first()
                if existe:
                    conn.execute(text("UPDATE unica_snd SET valor=:v WHERE serie=:serie "
                                      "AND safra=:safra AND data_ref=:d"), p)
                else:
                    conn.execute(text("""INSERT INTO unica_snd
                        (id,serie,safra,data_ref,valor,data_coleta)
                        VALUES(:id,:serie,:safra,:d,:v,:dc)"""), p)
                    n += 1
        return len(registros), n

    def run(self):
        return _rodar("unica_snd", self._coletar)


COLETORES_ETANOL.append(UnicaSndCollector)


# ── Petrobras — reajustes de preço nas refinarias ─────────────────────────
class PetrobrasReajustesCollector:
    """Cada anúncio de reajuste de diesel/gasolina, com preço antes e depois."""

    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        linhas = _linhas("petrobras_reajustes.csv")
        n = 0
        with get_engine().begin() as conn:
            for r in linhas:
                d = _data(r.get("data"))
                produto = (r.get("produto") or "").strip()
                if not d or not produto:
                    continue
                p = {"id": uuid.uuid4().hex, "d": d, "prod": produto,
                     "tipo": (r.get("tipo") or "").strip(),
                     "ant": _num(r.get("preco_anterior_rs_l")),
                     "novo": _num(r.get("preco_novo_rs_l")),
                     "dl": _num(r.get("delta_rs_l")),
                     "dp": _num(r.get("delta_pct")),
                     "desc": (r.get("descricao") or "").strip(),
                     "dc": datetime.utcnow()}
                existe = conn.execute(
                    text("SELECT 1 FROM petrobras_reajustes WHERE data_ref=:d "
                         "AND produto=:prod"), {"d": d, "prod": produto}).first()
                if existe:
                    conn.execute(text("""UPDATE petrobras_reajustes
                        SET tipo=:tipo, preco_anterior_rs_l=:ant,
                            preco_novo_rs_l=:novo, delta_rs_l=:dl, delta_pct=:dp,
                            descricao=:desc WHERE data_ref=:d AND produto=:prod"""), p)
                else:
                    conn.execute(text("""INSERT INTO petrobras_reajustes
                        (id,data_ref,produto,tipo,preco_anterior_rs_l,preco_novo_rs_l,
                         delta_rs_l,delta_pct,descricao,data_coleta)
                        VALUES(:id,:d,:prod,:tipo,:ant,:novo,:dl,:dp,:desc,:dc)"""), p)
                    n += 1
        return len(linhas), n

    def run(self):
        return _rodar("petrobras", self._coletar)


COLETORES_ETANOL.append(PetrobrasReajustesCollector)


# ── Petrobras — reajustes de preço nas refinarias ─────────────────────────
class PetrobrasReajustesCollector:
    """Histórico de reajustes de gasolina e diesel anunciados pela Petrobras."""

    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        linhas = _linhas("petrobras_reajustes.csv")
        n = 0
        with get_engine().begin() as conn:
            for r in linhas:
                d = _data(r.get("data"))
                produto = (r.get("produto") or "").strip()
                if not d or not produto:
                    continue
                p = {"id": uuid.uuid4().hex, "d": d, "prod": produto,
                     "tipo": (r.get("tipo") or "").strip(),
                     "ant": _num(r.get("preco_anterior_rs_l")),
                     "novo": _num(r.get("preco_novo_rs_l")),
                     "delta": _num(r.get("delta_rs_l")),
                     "pct": _num(r.get("delta_pct")),
                     "desc": (r.get("descricao") or "").strip()[:400],
                     "dc": datetime.utcnow()}
                existe = conn.execute(
                    text("SELECT 1 FROM petrobras_reajustes WHERE data_ref=:d "
                         "AND produto=:prod"), {"d": d, "prod": produto}).first()
                if existe:
                    conn.execute(text("""UPDATE petrobras_reajustes
                        SET preco_anterior_rs_l=:ant, preco_novo_rs_l=:novo,
                            delta_rs_l=:delta, delta_pct=:pct, descricao=:desc,
                            tipo=:tipo WHERE data_ref=:d AND produto=:prod"""), p)
                else:
                    conn.execute(text("""INSERT INTO petrobras_reajustes
                        (id,data_ref,produto,tipo,preco_anterior_rs_l,preco_novo_rs_l,
                         delta_rs_l,delta_pct,descricao,data_coleta)
                        VALUES(:id,:d,:prod,:tipo,:ant,:novo,:delta,:pct,:desc,:dc)"""), p)
                    n += 1
        return len(linhas), n

    def run(self):
        return _rodar("petrobras_reajustes", self._coletar)


COLETORES_ETANOL.append(PetrobrasReajustesCollector)
