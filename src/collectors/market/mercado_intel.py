"""Coletores das séries de mercado do sugar-intel (CFTC, curva, basis, finviz, ENSO).

Cada um baixa o CSV do sugar-intel e grava numa tabela própria (migração 0015).
São dados sem indicador direto no catálogo (posições, curvas, spreads), por isso
tabelas dedicadas. A aba Mercado lê dessas tabelas.

Atribuição: dados compilados pelo projeto sugar-intel (Igor Strongylis).
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime

import httpx
from sqlalchemy import text

from src.domain.models import CollectorResult
from src.persistence.db import get_engine
from src.persistence.repositories import log_run

BASE_URL = "https://strongylis.github.io/sugar-intel/data"
SOURCE_CODE = "sugar_intel"
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
}


def _num(v):
    s = str(v or "").strip().replace(",", "")
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _data(v):
    s = str(v or "").strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def _baixar(arquivo: str) -> str:
    resp = httpx.get(f"{BASE_URL}/{arquivo}", timeout=60,
                     follow_redirects=True, headers=_HEADERS)
    resp.raise_for_status()
    return resp.content.decode("utf-8", errors="replace")


def _rodar(nome_fonte, coletar_fn):
    started = datetime.utcnow()
    try:
        n_seen, n_new = coletar_fn()
        r = CollectorResult(source_code=SOURCE_CODE, started_at=started,
                            finished_at=datetime.utcnow(), rows_seen=n_seen,
                            rows_new=n_new, ok=True)
    except Exception as exc:  # noqa: BLE001
        r = CollectorResult(source_code=SOURCE_CODE, started_at=started,
                           finished_at=datetime.utcnow(), ok=False,
                           error=f"{nome_fonte}: {type(exc).__name__}: {exc}")
    log_run(r)
    return r


# ── CFTC posicionamento ───────────────────────────────────────────────────
class CftcSugarCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        texto = _baixar("cftc_sugar.csv")
        linhas = list(csv.DictReader(io.StringIO(texto)))
        n = 0
        with get_engine().begin() as conn:
            for r in linhas:
                d = _data(r.get("data"))
                if not d:
                    continue
                p = {"id": uuid.uuid4().hex, "d": d, "esp": _num(r.get("esp_net")),
                     "com": _num(r.get("com_net")), "idx": _num(r.get("idx_net")),
                     "oi": _num(r.get("open_interest")), "dc": datetime.utcnow()}
                existe = conn.execute(text("SELECT 1 FROM cftc_sugar WHERE data_ref=:d"),
                                      {"d": d}).first()
                if existe:
                    conn.execute(text("""UPDATE cftc_sugar SET esp_net=:esp, com_net=:com,
                        idx_net=:idx, open_interest=:oi WHERE data_ref=:d"""), p)
                else:
                    conn.execute(text("""INSERT INTO cftc_sugar
                        (id,data_ref,esp_net,com_net,idx_net,open_interest,data_coleta)
                        VALUES(:id,:d,:esp,:com,:idx,:oi,:dc)"""), p)
                    n += 1
        return len(linhas), n

    def run(self):
        return _rodar("cftc", self._coletar)


# ── Curva a termo NY11 (só a data mais recente de cada vencimento) ────────
class Ny11CurvaCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        texto = _baixar("ny11_curva.csv")
        linhas = list(csv.DictReader(io.StringIO(texto)))
        # para cada vencimento, fica só a data mais recente
        recentes: dict[str, dict] = {}
        for r in linhas:
            venc = (r.get("vencimento_codigo") or "").strip()
            d = _data(r.get("data"))
            if not venc or not d:
                continue
            if venc not in recentes or d > recentes[venc]["d"]:
                recentes[venc] = {
                    "venc": venc, "mes": (r.get("mes_nome") or "").strip(),
                    "ano": r.get("ano_vencimento"), "d": d,
                    "close": _num(r.get("close"))}
        n = 0
        with get_engine().begin() as conn:
            conn.execute(text("DELETE FROM ny11_curva"))  # snapshot: sempre o atual
            for x in recentes.values():
                try:
                    ano = int(str(x["ano"])[:4])
                except (ValueError, TypeError):
                    ano = None
                conn.execute(text("""INSERT INTO ny11_curva
                    (id,vencimento,mes_nome,ano_venc,data_ref,close_clb,data_coleta)
                    VALUES(:id,:v,:m,:a,:d,:c,:dc)"""),
                    {"id": uuid.uuid4().hex, "v": x["venc"], "m": x["mes"],
                     "a": ano, "d": x["d"], "c": x["close"], "dc": datetime.utcnow()})
                n += 1
        return len(linhas), n

    def run(self):
        return _rodar("ny11_curva", self._coletar)


# ── Basis ESALQ vs NY ─────────────────────────────────────────────────────
class BasisAcucarCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        texto = _baixar("basis_acucar.csv")
        linhas = list(csv.DictReader(io.StringIO(texto)))
        n = 0
        with get_engine().begin() as conn:
            for r in linhas:
                d = _data(r.get("data"))
                if not d:
                    continue
                p = {"id": uuid.uuid4().hex, "d": d,
                     "es": _num(r.get("esalq_rs_sc50kg")),
                     "ny": _num(r.get("ny_equiv_rs_sc50kg")),
                     "clb": _num(r.get("ny_cont_clb")),
                     "ptax": _num(r.get("usd_ptax")), "dc": datetime.utcnow()}
                existe = conn.execute(text("SELECT 1 FROM basis_acucar WHERE data_ref=:d"),
                                      {"d": d}).first()
                if existe:
                    conn.execute(text("""UPDATE basis_acucar SET esalq_rs_sc50kg=:es,
                        ny_equiv_rs_sc50kg=:ny, ny_cont_clb=:clb, usd_ptax=:ptax
                        WHERE data_ref=:d"""), p)
                else:
                    conn.execute(text("""INSERT INTO basis_acucar
                        (id,data_ref,esalq_rs_sc50kg,ny_equiv_rs_sc50kg,ny_cont_clb,
                         usd_ptax,data_coleta)
                        VALUES(:id,:d,:es,:ny,:clb,:ptax,:dc)"""), p)
                    n += 1
        return len(linhas), n

    def run(self):
        return _rodar("basis", self._coletar)


# ── finviz (snapshot de performance) ──────────────────────────────────────
class FinvizCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        texto = _baixar("finviz.csv")
        linhas = list(csv.DictReader(io.StringIO(texto)))
        n = 0
        with get_engine().begin() as conn:
            for r in linhas:
                dc = _data(r.get("data_coleta")) or date.today()
                tk = (r.get("ticker") or "").strip()
                if not tk:
                    continue
                p = {"id": uuid.uuid4().hex, "dc": dc, "tk": tk,
                     "nome": (r.get("nome") or "").strip(),
                     "cat": (r.get("categoria") or "").strip(),
                     "w": _num(r.get("perf_1w_pct")), "m": _num(r.get("perf_1m_pct")),
                     "ytd": _num(r.get("perf_ytd_pct")), "y": _num(r.get("perf_1y_pct"))}
                existe = conn.execute(
                    text("SELECT 1 FROM finviz_perf WHERE ticker=:tk AND data_coleta=:dc"),
                    {"tk": tk, "dc": dc}).first()
                if existe:
                    conn.execute(text("""UPDATE finviz_perf SET perf_1w=:w, perf_1m=:m,
                        perf_ytd=:ytd, perf_1y=:y, nome=:nome, categoria=:cat
                        WHERE ticker=:tk AND data_coleta=:dc"""), p)
                else:
                    conn.execute(text("""INSERT INTO finviz_perf
                        (id,data_coleta,ticker,nome,categoria,perf_1w,perf_1m,perf_ytd,perf_1y)
                        VALUES(:id,:dc,:tk,:nome,:cat,:w,:m,:ytd,:y)"""), p)
                    n += 1
        return len(linhas), n

    def run(self):
        return _rodar("finviz", self._coletar)


# ── ENSO (El Niño) — snapshot ─────────────────────────────────────────────
class EnsoCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        texto = _baixar("enso.csv")
        linhas = list(csv.DictReader(io.StringIO(texto)))
        n = 0
        with get_engine().begin() as conn:
            for r in linhas:
                dc = _data(r.get("data_coleta")) or date.today()
                p = {"id": uuid.uuid4().hex, "dc": dc,
                     "al": (r.get("alert_status") or "").strip(),
                     "fase": (r.get("fase_oni_atual") or "").strip(),
                     "tri": (r.get("trimestre_oni_atual") or "").strip(),
                     "oni": _num(r.get("oni_anom_atual_C")),
                     "n34": _num(r.get("nino34_weekly_C")),
                     "sin": (r.get("sinopse") or "").strip()}
                existe = conn.execute(text("SELECT 1 FROM enso_status WHERE data_coleta=:dc"),
                                      {"dc": dc}).first()
                if existe:
                    conn.execute(text("""UPDATE enso_status SET alert_status=:al,
                        fase_oni=:fase, trimestre_oni=:tri, oni_anom_c=:oni,
                        nino34_c=:n34, sinopse=:sin WHERE data_coleta=:dc"""), p)
                else:
                    conn.execute(text("""INSERT INTO enso_status
                        (id,data_coleta,alert_status,fase_oni,trimestre_oni,oni_anom_c,
                         nino34_c,sinopse)
                        VALUES(:id,:dc,:al,:fase,:tri,:oni,:n34,:sin)"""), p)
                    n += 1
        return len(linhas), n

    def run(self):
        return _rodar("enso", self._coletar)


COLETORES_MERCADO = [
    CftcSugarCollector, Ny11CurvaCollector, BasisAcucarCollector,
    FinvizCollector, EnsoCollector,
]


# ── IRI — pluma de previsão do ENSO (snapshot da emissão atual) ───────────
class IriPlumeCollector:
    """Projeções de anomalia Niño 3.4 por modelo, trimestre a trimestre."""

    source_code = SOURCE_CODE
    version = "0.1.0"

    def _coletar(self):
        texto = _baixar("iri_plume.csv")
        linhas = list(csv.DictReader(io.StringIO(texto)))
        n = 0
        with get_engine().begin() as conn:
            conn.execute(text("DELETE FROM iri_plume"))  # snapshot da emissão atual
            for r in linhas:
                d = _data(r.get("data_prev"))
                modelo = (r.get("modelo") or "").strip()
                if not d or not modelo:
                    continue
                try:
                    passo = int(str(r.get("passo") or 0).strip() or 0)
                except ValueError:
                    passo = 0
                conn.execute(text("""INSERT INTO iri_plume
                    (id,data_coleta,emissao,passo,estacao,data_prev,modelo,tipo,
                     nino34_anom_c)
                    VALUES(:id,:dc,:em,:pa,:es,:d,:mo,:ti,:v)"""),
                    {"id": uuid.uuid4().hex,
                     "dc": _data(r.get("data_coleta")) or date.today(),
                     "em": (r.get("emissao") or "").strip(), "pa": passo,
                     "es": (r.get("estacao") or "").strip(), "d": d, "mo": modelo,
                     "ti": (r.get("tipo") or "").strip(),
                     "v": _num(r.get("nino34_anom_C"))})
                n += 1
        return len(linhas), n

    def run(self):
        return _rodar("iri_plume", self._coletar)


COLETORES_MERCADO.append(IriPlumeCollector)
