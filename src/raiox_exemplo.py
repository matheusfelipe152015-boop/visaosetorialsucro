# ruff: noqa: E501
"""Carteira de exemplo (fictícia) para testar o Raio X sem a base real.

TODOS os dados aqui são inventados — usinas, grupos e valores não correspondem a
nenhuma empresa real. Serve só para exercitar as telas, o de-para e os
comentários durante os testes. Depois de validar, este arquivo pode ser removido.

As colunas seguem os nomes reais da carteira (idGrupo, nomeGrupo, valorRisco...),
para o teste ser fiel ao formato de produção.
"""

from __future__ import annotations

import pandas as pd

# 20 grupos fictícios, com valores plausíveis para o setor
_LINHAS = [
    # (idGrupo, nomeGrupo, valorRisco, valorLimite, analista, rating, setor, gerente, uf)
    (1001, "Usina Aurora do Vale", 82_000_000, 100_000_000, "Ana Ribeiro", "Ba1", "Sucroenergético", "Carlos M.", "SP"),
    (1002, "Grupo Canavial Real", 145_000_000, 180_000_000, "Bruno Costa", "Baa4", "Sucroenergético", "Carlos M.", "SP"),
    (1003, "Agroenergia São Jorge", 47_000_000, 60_000_000, "Ana Ribeiro", "Ba4", "Sucroenergético", "Dora L.", "GO"),
    (1004, "Destilaria Boa Vista", 23_000_000, 30_000_000, "Bruno Costa", "B2", "Sucroenergético", "Dora L.", "MG"),
    (1005, "Usina Campo Verde", 210_000_000, 250_000_000, "Ana Ribeiro", "Baa1", "Sucroenergético", "Carlos M.", "SP"),
    (1006, "Bioenergia Cerrado", 68_000_000, 90_000_000, "Elena Souza", "Ba1", "Sucroenergético", "Dora L.", "MT"),
    (1007, "Grupo Açúcar Dourado", 156_000_000, 175_000_000, "Bruno Costa", "Ba4", "Sucroenergético", "Carlos M.", "SP"),
    (1008, "Usina Rio Doce", 34_000_000, 45_000_000, "Elena Souza", "B1", "Sucroenergético", "Dora L.", "MG"),
    (1009, "Cana & Cia", 91_000_000, 110_000_000, "Ana Ribeiro", "Ba6", "Sucroenergético", "Dora L.", "PR"),
    (1010, "Etanol Nordeste", 55_000_000, 70_000_000, "Elena Souza", "Ba4", "Sucroenergético", "Fábio R.", "AL"),
    (1011, "Grãos do Planalto", 120_000_000, 140_000_000, "Bruno Costa", "Baa4", "Grãos", "Fábio R.", "MT"),
    (1012, "Agro Sementes Sul", 38_000_000, 50_000_000, "Ana Ribeiro", "B2", "Grãos", "Fábio R.", "RS"),
    (1013, "Cereais União", 74_000_000, 85_000_000, "Elena Souza", "Ba1", "Grãos", "Fábio R.", "GO"),
    (1014, "Proteína Animal BR", 98_000_000, 120_000_000, "Bruno Costa", "Ba4", "Proteína", "Carlos M.", "SP"),
    (1015, "Frigorífico Central", 42_000_000, 55_000_000, "Ana Ribeiro", "B1", "Proteína", "Dora L.", "MS"),
    (1016, "Laticínios Bela Vista", 29_000_000, 40_000_000, "Elena Souza", "B4", "Proteína", "Fábio R.", "MG"),
    (1017, "Usina Sol Nascente", 187_000_000, 200_000_000, "Bruno Costa", "Baa4", "Sucroenergético", "Carlos M.", "SP"),
    (1018, "Bioetanol Triângulo", 63_000_000, 80_000_000, "Ana Ribeiro", "Ba4", "Sucroenergético", "Dora L.", "MG"),
    (1019, "Grupo Verde Cana", 112_000_000, 130_000_000, "Elena Souza", "Ba1", "Sucroenergético", "Carlos M.", "SP"),
    (1020, "Açúcar & Energia MT", 79_000_000, 95_000_000, "Bruno Costa", "C1", "Sucroenergético", "Fábio R.", "MT"),
]


def carteira_exemplo() -> pd.DataFrame:
    """Devolve a carteira fictícia no formato da planilha real."""
    linhas = []
    for (idg, nome, risco, limite, analista, rating, setor, gerente, uf) in _LINHAS:
        linhas.append({
            "idGrupo": idg,
            "nomeGrupo": nome,
            "valorRisco": risco,
            "valorLimite": limite,
            "valorLimiteDisponivel": limite - risco,
            "analista": analista,
            "rating": rating,
            "setorGerencialPodicre": setor,
            "gerente": gerente,
            "regiao": uf,
        })
    return pd.DataFrame(linhas)
