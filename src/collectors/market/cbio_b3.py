"""Coletor do preco do CBIO (Credito de Descarbonizacao) — B3.

A API funciona, mas e instavel de fora (as vezes retorna vazio). Por isso:
tenta cada data disponivel ate achar negocios; se nada vier, NAO grava (nunca
inventa numero). Rodando durante o pregao a taxa de sucesso e melhor.
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


def _url_lista(data_iso, page_size=500):
    payload = {"lang": "pt-br", "pageNumber": 1, "pageSize": page_size,
               "bondType": "CBIO", "date": data_iso}
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


def parse_cbio(payload, ref):
    """Media ponderada pela quantidade dos negocios de CBIO."""
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
        preco = _num(lin.get("tradePrice") or lin.get("price") or lin.get("Price"))
        qtd = _num(lin.get("tradeQuantity") or lin.get("quantity") or lin.get("Quantity"))
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
        collector_version="0.3.0",
        status_validacao=ValidationStatus.OK,
        url_original="https://www.b3.com.br/pt_br/b3/sustentabilidade/produtos-e-servicos-esg/credito-de-descarbonizacao-cbio/cbio-negocios-realizados-hoje/",
    )


class CbioB3Collector(Collector):
    source_code = SOURCE_CODE
    version = "0.3.0"

    def collect(self):
        with httpx.Client(follow_redirects=True) as client:
            datas = client.get(URL_DATAS, timeout=30, headers=HEADERS).json()
            if isinstance(datas, str):
                datas = json.loads(datas)
            datas = [d[:10] for d in datas if isinstance(d, str) and len(d) >= 10]
            for data_iso in datas[:10]:
                resp = client.get(_url_lista(data_iso), timeout=30, headers=HEADERS)
                resp.raise_for_status()
                ref = date.fromisoformat(data_iso)
                iv = parse_cbio(resp.json(), ref)
                if iv:
                    return [iv]
            return []
