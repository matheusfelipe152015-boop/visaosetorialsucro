"""Coletor ANP — preços de combustíveis (pesquisa semanal de revenda).

Fonte: ANP, Série Histórica de Preços de Combustíveis (dados abertos, CC0).
Os arquivos são CSV por período/produto, separados por ';' e com vírgula no
decimal (padrão BR), com uma linha por posto pesquisado. Aqui resumimos para a
**média nacional por combustível**, por data de coleta (a pesquisa é semanal).

Colunas relevantes: 'Produto', 'Valor de Venda', 'Data da Coleta'.

A agregação (parse_precos) é separada do download para ser testável offline
(ver tests/test_anp.py). O download real roda na máquina do usuário; o ambiente
de desenvolvimento não acessa o site da ANP.
"""

from __future__ import annotations

import io
from datetime import date, datetime

import httpx
import pandas as pd

from src.collectors.base import Collector
from src.domain.enums import ValidationStatus
from src.domain.models import IndicatorValue

SOURCE_CODE = "anp"

# Base dos arquivos abertos da ANP (gasolina/etanol no mesmo arquivo mensal).
ANP_URL = (
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/"
    "arquivos/shpc/dsan/{ano}/{ano}-{mes:02d}-gasolina-etanol.csv"
)

# Produto (como aparece no CSV) -> indicador na plataforma.
PRODUTO_INDICADOR: dict[str, tuple[str, str]] = {
    # produto_no_csv : (indicator_code, nome_amigavel)
    "GASOLINA": ("preco_gasolina", "Gasolina comum (revenda)"),
    "GASOLINA ADITIVADA": ("preco_gasolina_aditivada", "Gasolina aditivada (revenda)"),
    "ETANOL": ("preco_etanol", "Etanol hidratado (revenda)"),
}


def parse_precos(csv_bytes: bytes) -> list[IndicatorValue]:
    """Lê o CSV bruto da ANP e devolve a média nacional por combustível.

    Uma linha de saída por (produto, data de referência), com o preço médio
    de venda no país naquela pesquisa.
    """
    df = pd.read_csv(
        io.BytesIO(csv_bytes),
        sep=";",
        decimal=",",
        encoding="latin-1",
        usecols=lambda c: c.strip() in ("Produto", "Valor de Venda", "Data da Coleta"),
    )
    df.columns = [c.strip() for c in df.columns]
    df["Produto"] = df["Produto"].str.upper().str.strip()
    df["data_ref"] = pd.to_datetime(df["Data da Coleta"], dayfirst=True).dt.date

    out: list[IndicatorValue] = []
    for produto, (code, _nome) in PRODUTO_INDICADOR.items():
        sub = df[df["Produto"] == produto]
        if sub.empty:
            continue
        # média nacional por data de coleta (a pesquisa cobre vários dias da semana)
        for ref, grupo in sub.groupby("data_ref"):
            media = float(grupo["Valor de Venda"].mean())
            out.append(
                IndicatorValue(
                    indicator_code=code,
                    source_code=SOURCE_CODE,
                    data_referencia=ref,
                    valor=round(media, 4),
                    unidade="R$/L",
                    moeda="BRL",
                    escala="unit",
                    data_publicacao=ref,
                    data_coleta=datetime.utcnow(),
                    collector_version="0.1.0",
                    status_validacao=ValidationStatus.OK,
                    url_original="https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos",
                )
            )
    return out


class AnpPrecosCollector(Collector):
    source_code = SOURCE_CODE
    version = "0.1.0"

    def __init__(self, ano: int | None = None, mes: int | None = None) -> None:
        hoje = date.today()
        self.ano = ano or hoje.year
        self.mes = mes or hoje.month

    def collect(self) -> list[IndicatorValue]:
        url = ANP_URL.format(ano=self.ano, mes=self.mes)
        resp = httpx.get(
            url,
            timeout=120,
            follow_redirects=True,
            headers={"User-Agent": "canavis/0.1 (intel-sucroenergetico)"},
        )
        resp.raise_for_status()
        return parse_precos(resp.content)
