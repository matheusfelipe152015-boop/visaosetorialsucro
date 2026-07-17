"""Coletor do preço do CBIO (Crédito de Descarbonização) — B3.

Fonte: sistema de negócios de balcão da B3. A API precisa de DOIS passos:
  1. GetAvailableDates -> lista de datas com pregão disponível;
  2. GetList (com a data escolhida, em base64) -> negócios daquele dia.

A B3 disponibiliza os negócios com um dia de defasagem (o pregão de hoje só
aparece no dia seguinte). Por isso pegamos sempre a data mais recente da lista.

Cada linha é um negócio; o preço do dia é a MÉDIA PONDERADA pela quantidade.
Se não houver negócio, não grava nada (não inventa número).
"""

from __future__ import annotations

import base64
import json
from datetime import date, datetime

import httpx

from src.collectors.base import Collector
from src.domain.enums import ValidationStatus
from src.domain.models import IndicatorValue

SOURCE_CODE = "b3"
BASE = "https://sistemaswebb3-balcao.b3.com.br/tradesClosedProxy/TradesClosedCall/"
URL_DATAS = BASE + "GetAvailableDates"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://sistemaswebb3-balcao.b3.com.br/",
}


def _url_lista(data_iso: str, page_size: int = 500) -> str:
    """URL do GetList para uma data específica (parâmetros em base64)."""
    payload = {
        "lang": "pt-br",
        "pageNumber": 1,
        "pageSize": page_size,
        "bondType": "CBIO",
        "date": data_iso,
    }
    enc = base64.b64encode(json.dumps(payload).encode()).decode()
    return BASE + "GetList/" + enc


def _num(v):
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_cbio(payload: dict, ref: date) -> IndicatorValue | None:
    """Média ponderada pela quantidade dos negócios de CBIO."""
    linhas = None
    for chave in ("results", "Trades", "trades", "dados", "value"):
        if isinstance(payload.get(chave), list):
            linhas = payload[chave]
            break
    if linhas is None and isinstance(payload, list):
        linhas = payload
    if not linhas:
        return None

    soma_valor = 0.0
    soma_qtd = 0.0
    for lin in linhas:
        preco = _num(
            lin.get("price") or lin.get("Price")
            or lin.get("tradePrice") or lin.get("precoNegocio")
            or lin.get("PrecoDoNegocio") or lin.get("prc")
        )
        qtd = _num(
            lin.get("quantity") or lin.get("Quantity")
            or lin.get("tradeQuantity") or lin.get("quantidadeNegociada")
            or lin.get("QtdNegociada") or lin.get("qty")
        )
        if preco is None:
            continue
        peso = qtd if qtd else 1.0
        soma_valor += preco * peso
        soma_qtd += peso

    if soma_qtd == 0:
        return None
    media = round(soma_valor / soma_qtd, 2)
    return IndicatorValue(
        indicator_code="cbio",
        source_code=SOURCE_CODE,
        data_referencia=ref,
        valor=media,
        unidade="R$/un",
        moeda="BRL",
        escala="unit",
        data_publicacao=ref,
        data_coleta=datetime.utcnow(),
        collector_version="0.2.0",
        status_validacao=ValidationStatus.OK,
        url_original="https://www.b3.com.br/pt_br/b3/sustentabilidade/produtos-e-servicos-esg/credito-de-descarbonizacao-cbio/cbio-negocios-realizados-hoje/",
    )


class CbioB3Collector(Collector):
    source_code = SOURCE_CODE
    version = "0.2.0"

    def _datas_disponiveis(self, client: httpx.Client) -> list[str]:
        resp = client.get(URL_DATAS, timeout=30, headers=HEADERS)
        resp.raise_for_status()
        datas = resp.json()
        # vem como ["2026-07-13T00:00:00", ...] — já em ordem decrescente
        return [d[:10] for d in datas if isinstance(d, str)]

    def collect(self) -> list[IndicatorValue]:
        with httpx.Client(follow_redirects=True) as client:
            datas = self._datas_disponiveis(client)
            if not datas:
                return []
            # tenta as 3 datas mais recentes até achar negócios
            for data_iso in datas[:7]:
                url = _url_lista(data_iso)
                resp = client.get(url, timeout=30, headers=HEADERS)
                resp.raise_for_status()
                ref = date.fromisoformat(data_iso)
                iv = parse_cbio(resp.json(), ref)
                if iv:
                    return [iv]
        return []
