"""Catálogo de fontes de RI (Relações com Investidores) por empresa.

Mapa que o coletor real usará para saber ONDE buscar os releases de cada
usina de capital aberto. Por enquanto é o cadastro (endereços e observações);
a coleta efetiva (baixar o PDF, extrair texto, rodar o release_reader) é o
próximo passo, idealmente validado com a Maju no PC.

Campos:
  - ri_url: página de RI / central de resultados
  - formato: como o release costuma vir (pdf, html)
  - rastreavel: se dá para aplicar a busca por palavras-chave hoje
  - obs: anotações honestas sobre dificuldade/particularidade
"""

from __future__ import annotations

RI_FONTES: dict[str, dict] = {
    "sao_martinho": {
        "nome": "São Martinho",
        "ticker": "SMTO3",
        "ri_url": "https://ri.saomartinho.com.br/",
        "formato": "pdf",
        "rastreavel": True,
        "obs": "Release de produção trimestral bem padronizado. Melhor candidata para começar.",
    },
    "jalles": {
        "nome": "Jalles Machado",
        "ticker": "JALL3",
        "ri_url": "https://ri.jallesmachado.com/",
        "formato": "pdf",
        "rastreavel": True,
        "obs": "Release com seções de açúcar orgânico; rótulos padronizados.",
    },
    "raizen": {
        "nome": "Raízen",
        "ticker": "RAIZ4",
        "ri_url": "https://ri.raizen.com.br/",
        "formato": "pdf",
        "rastreavel": True,
        "obs": "Empresa grande; release extenso. Atenção a múltiplas ocorrências dos rótulos.",
    },
    "cosan": {
        "nome": "Cosan",
        "ticker": "CSAN3",
        "ri_url": "https://ri.cosan.com.br/",
        "formato": "pdf",
        "rastreavel": False,
        "obs": "Holding (vários negócios além de cana). Dado sucroenergético vem via Raízen; "
               "extrair direto da Cosan mistura segmentos. Preferir Raízen para operacional.",
    },
    "adecoagro": {
        "nome": "Adecoagro",
        "ticker": "AGRO",
        "ri_url": "https://www.adecoagro.com/InvestorRelations",
        "formato": "pdf",
        "rastreavel": False,
        "obs": "NYSE, release em inglês e multi-país (Argentina/Brasil/Uruguai). "
               "Sinônimos teriam de ser em inglês e separar o Brasil. Fase 2.",
    },
    "ctc": {
        "nome": "CTC · Centro de Tecnologia Canavieira",
        "ticker": "CTCA3",
        "ri_url": "https://ri.ctc.com.br/",
        "formato": "pdf",
        "rastreavel": False,
        "obs": "Não é usina: tecnologia/genética de cana (royalties). Sem moagem própria. "
               "Acompanhamento institucional, fora do comparativo de moagem.",
    },
}


def fontes_rastreaveis() -> list[str]:
    """Empresas onde a busca por palavras-chave se aplica hoje."""
    return [code for code, f in RI_FONTES.items() if f["rastreavel"]]
