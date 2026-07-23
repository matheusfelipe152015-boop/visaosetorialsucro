"""Coletores das séries abertas do sugar-intel (CSV) → indicator_values.

Cada série do sugar-intel vira valores de um indicador já existente no catálogo.
Todos herdam de _CsvIndicatorCollector, que baixa o CSV, chama um parser
específico e faz o upsert idempotente.

Atribuição: dados compilados pelo projeto sugar-intel (Igor Strongylis) a partir
de CEPEA/ESALQ, UNICA, EIA, USDA e Yahoo. Uso interno; validar licença de
redistribuição antes de uso institucional amplo.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

import httpx

from src.domain.enums import ValidationStatus
from src.domain.models import CollectorResult, IndicatorValue
from src.persistence.repositories import log_run, upsert_indicator_values

BASE_URL = "https://strongylis.github.io/sugar-intel/data"
SOURCE_CODE = "sugar_intel"
_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
}


def _num(v):
    s = str(v or "").strip().replace(",", "")
    if not s or s.lower() in ("nan", "none", "null", ""):
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


class _CsvIndicatorCollector:
    """Base: baixa <BASE_URL>/<arquivo> e grava via parse() -> IndicatorValue[]."""

    source_code = SOURCE_CODE
    version = "0.1.0"
    arquivo = ""      # ex.: "cepea_acucar_sp.csv"

    def _url(self) -> str:
        return f"{BASE_URL}/{self.arquivo}"

    def parse(self, texto: str) -> list[IndicatorValue]:  # noqa: D401
        raise NotImplementedError

    def collect(self) -> list[IndicatorValue]:
        resp = httpx.get(self._url(), timeout=60, follow_redirects=True,
                         headers=_HEADERS)
        resp.raise_for_status()
        return self.parse(resp.content.decode("utf-8", errors="replace"))

    def run(self) -> CollectorResult:
        started = datetime.utcnow()
        try:
            valores = self.collect()
            n = upsert_indicator_values(valores)
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), rows_seen=len(valores),
                rows_new=n, ok=True)
        except Exception as exc:  # noqa: BLE001
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), ok=False,
                error=f"{type(exc).__name__}: {exc}")
        log_run(result)
        return result


def _iv(code, d, valor, unidade, moeda=None, url=None) -> IndicatorValue:
    return IndicatorValue(
        indicator_code=code, source_code=SOURCE_CODE, data_referencia=d,
        valor=valor, unidade=unidade, moeda=moeda, url_original=url,
        status_validacao=ValidationStatus.OK)


# ── Açúcar cristal ESALQ (SP) — R$/sc 50kg ────────────────────────────────
class CepeaAcucarSpCollector(_CsvIndicatorCollector):
    arquivo = "cepea_acucar_sp.csv"

    def parse(self, texto):
        out = []
        for r in csv.DictReader(io.StringIO(texto)):
            d = _data(r.get("data"))
            v = _num(r.get("preco_r$_sc50kg"))
            if d and v is not None:
                out.append(_iv("acucar_cristal_sp", d, v, "R$/sc", "BRL", self._url()))
        return out


# ── Etanol hidratado/anidro CEPEA (SP) — R$/L ─────────────────────────────
class CepeaEtanolSpCollector(_CsvIndicatorCollector):
    arquivo = "cepea_etanol_sp.csv"

    def parse(self, texto):
        out = []
        for r in csv.DictReader(io.StringIO(texto)):
            d = _data(r.get("semana_inicio"))
            if not d:
                continue
            hid = _num(r.get("preco_hidratado_r$_l"))
            ani = _num(r.get("preco_anidro_r$_l"))
            if hid is not None:
                out.append(_iv("etanol_hidratado", d, hid, "R$/L", "BRL", self._url()))
            if ani is not None:
                out.append(_iv("etanol_anidro_sp", d, ani, "R$/L", "BRL", self._url()))
        return out


# ── Brent — US$/bbl (fonte oil.csv, coluna brent) ─────────────────────────
class OilBrentCollector(_CsvIndicatorCollector):
    arquivo = "oil.csv"

    def parse(self, texto):
        out = []
        for r in csv.DictReader(io.StringIO(texto)):
            d = _data(r.get("data"))
            v = _num(r.get("brent_usd_bbl"))
            if d and v is not None:
                out.append(_iv("brent", d, v, "US$/bbl", "USD", self._url()))
        return out


# ── UNICA quinzenal — moagem, mix e ATR (Centro-Sul, acumulado) ───────────
class UnicaQuinzenalCollector(_CsvIndicatorCollector):
    arquivo = "unica_quinzenal.csv"

    def parse(self, texto):
        out = []
        for r in csv.DictReader(io.StringIO(texto)):
            if (r.get("regiao") or "").strip() != "Centro-Sul":
                continue
            if (r.get("tipo_secao") or "").strip() != "acumulado":
                continue
            d = _data(r.get("quinzena_fim"))
            if not d:
                continue
            moagem = _num(r.get("cana_mil_t"))
            mix_ac = _num(r.get("mix_acucar_pct"))
            atr = _num(r.get("atr_kg_t_cana"))
            if moagem is not None:
                out.append(_iv("moagem_cs", d, moagem, "mil t", None, self._url()))
            if mix_ac is not None:
                out.append(_iv("mix_acucar_etanol", d, mix_ac, "%", None, self._url()))
            if atr is not None:
                out.append(_iv("atr_medio", d, atr, "kg/t", None, self._url()))
        return out


# ── USDA açúcar — produção e estoque (anual) ──────────────────────────────
class UsdaAcucarCollector(_CsvIndicatorCollector):
    arquivo = "usda_acucar.csv"

    def parse(self, texto):
        out = []
        for r in csv.DictReader(io.StringIO(texto)):
            ano = str(r.get("ano_safra") or "").strip()[:4]
            if not ano.isdigit():
                continue
            d = date(int(ano), 12, 31)
            prod = _num(r.get("producao"))
            est = _num(r.get("estoque_final"))
            if prod is not None:
                out.append(_iv("usda_acucar_prod", d, prod, "mil t", None, self._url()))
            if est is not None:
                out.append(_iv("usda_acucar_estoque", d, est, "mil t", None, self._url()))
        return out


# ── Etanol hidratado Paulínia (CEPEA) — R$/m³, diário ─────────────────────
class CepeaEtanolPauliniaCollector(_CsvIndicatorCollector):
    """Benchmark do hidratado mais usado pelo setor (indicador diário)."""

    arquivo = "cepea_etanol_paulinia.csv"

    def parse(self, texto):
        out = []
        for r in csv.DictReader(io.StringIO(texto)):
            d = _data(r.get("data"))
            v = _num(r.get("preco_r$_m3"))
            if d and v is not None:
                out.append(_iv("etanol_paulinia", d, v, "R$/m³", "BRL", self._url()))
        return out


# ── ANP — vendas mensais de etanol hidratado (Brasil) ─────────────────────
class AnpVendasHidratadoCollector(_CsvIndicatorCollector):
    """Soma as vendas de hidratado de todas as UFs por mês."""

    arquivo = "anp_vendas.csv"

    def parse(self, texto):
        totais: dict[date, float] = {}
        for r in csv.DictReader(io.StringIO(texto)):
            produto = (r.get("produto") or "").strip().upper()
            if "ETANOL" not in produto or "HIDRATADO" not in produto:
                continue
            v = _num(r.get("vendas_m3"))
            try:
                ano, mes = int(r.get("ano")), int(r.get("mes"))
            except (TypeError, ValueError):
                continue
            if v is None:
                continue
            d = date(ano, mes, 1)
            totais[d] = totais.get(d, 0.0) + v
        return [_iv("vendas_combustiveis", d, v, "m³", None, self._url())
                for d, v in sorted(totais.items())]


COLETORES_SUGAR_INTEL = [
    CepeaAcucarSpCollector, CepeaEtanolSpCollector, OilBrentCollector,
    UnicaQuinzenalCollector, UsdaAcucarCollector,
    CepeaEtanolPauliniaCollector, AnpVendasHidratadoCollector,
]
