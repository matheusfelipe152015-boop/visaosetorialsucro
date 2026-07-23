"""Entrypoint da rotina diária (chamado pelo agendador).

Roda os coletores em sequência, cada um isolado: se uma fonte falhar, as
demais seguem normalmente (a página de Saúde registra o que deu certo e o que
não deu). Toda coleta é idempotente — pode rodar quantas vezes quiser sem
duplicar registros.

Para adicionar uma fonte nova, basta incluí-la na lista COLETORES.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.catalog import register_catalog
from src.collectors.base import Collector
from src.collectors.market.anp_precos import AnpPrecosCollector
from src.collectors.market.bcb_macro import BcbMacroCollector
from src.collectors.market.bcb_ptax import BcbPtaxCollector
from src.collectors.market.cbio_b3 import CbioB3Collector
from src.collectors.market.chuva_previsao import ChuvaPrevisaoCollector
from src.collectors.market.comex_export import ComexExportCollector
from src.collectors.market.conab_cana import ConabCanaCollector
from src.collectors.market.cotacoes_intl import CotacoesIntlCollector
from src.collectors.market.cvm_financeiro import CvmFinanceiroCollector
from src.collectors.market.etanol_intel import COLETORES_ETANOL
from src.collectors.market.mercado_intel import COLETORES_MERCADO
from src.collectors.market.sugar_intel_csv import COLETORES_SUGAR_INTEL
from src.collectors.news.rss_setor import RssNoticiasCollector
from src.persistence.db import get_engine, init_schema


def _preparar_catalogo() -> None:
    """Garante que fontes e indicadores existam antes de coletar (banco novo)."""
    with get_engine().begin() as conn:
        register_catalog(conn)


def coletores() -> list[Collector]:
    return [
        BcbPtaxCollector(days=1825),   # câmbio USD/BRL (~5 anos)
        BcbMacroCollector(days=365),   # Selic, IPCA, IGP-M, CDI (~2 anos)
        AnpPrecosCollector(),          # preços de combustíveis (mês corrente)
        ComexExportCollector(),
        CotacoesIntlCollector(),
        CbioB3Collector(),             # CBIO (B3)
        ConabCanaCollector(),          # safra de cana (CONAB)
        ChuvaPrevisaoCollector(),      # previsão de chuva 14 dias (sugar-intel)
        *[C() for C in COLETORES_SUGAR_INTEL],  # CEPEA, oil, UNICA, USDA (sugar-intel)
        *[C() for C in COLETORES_MERCADO],  # CFTC, curva NY11, basis, finviz, ENSO
        *[C() for C in COLETORES_ETANOL],  # B3 etanol, base SP-GO, ABICOM
        CvmFinanceiroCollector(),
        RssNoticiasCollector(),        # radar de manchetes (RSS)
    ]


def main() -> None:
    init_schema()
    _preparar_catalogo()
    falhas = 0
    lista = coletores()
    for col in lista:
        result = col.run()
        status = "OK" if result.ok else "FALHA"
        print(
            f"[{status}] {result.source_code}: {result.rows_seen} lidos, "
            f"{result.rows_new} novos, {result.duration_s:.1f}s"
        )
        if result.error:
            falhas += 1
            print("  erro:", result.error)
    print(f"\nConcluído: {len(lista)} fontes, {falhas} com falha.")


if __name__ == "__main__":
    main()
