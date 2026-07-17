"""Testa o de-para: salvar por ID, aplicar na carteira, ativo/inativo."""

import pandas as pd


def test_salva_e_aplica_analista_setor():
    from src.depara import aplicar_depara, salvar_linha_depara
    from src.raiox import normalize_base
    # de-para: cliente 10 muda de analista e setor
    salvar_linha_depara("10", "Ana Nova", "Setor Novo", 1, "tester")
    df = pd.DataFrame({
        "ID": [10, 20], "Nome do grupo": ["A", "B"],
        "Analista Podicre": ["Antigo", "Bruno"],
        "Agrupamento Setor Gerencial": ["Setor Velho", "Grãos"],
        "Risco Mês Atual Podicre": [100, 200],
        "Limite mês Atual Podicre": [100, 200],
    })
    base = normalize_base(df)
    out = aplicar_depara(base)
    linha = out[out["id"] == "10"].iloc[0]
    assert linha["analista"] == "Ana Nova"
    assert linha["setor_gerencial"] == "Setor Novo"
    # cliente 20 fica intacto
    assert out[out["id"] == "20"].iloc[0]["analista"] == "Bruno"


def test_inativo_some_da_carteira():
    from src.depara import aplicar_depara, salvar_linha_depara
    from src.raiox import normalize_base
    salvar_linha_depara("30", "X", "Y", 0, "tester")   # inativo
    df = pd.DataFrame({
        "ID": [30, 31], "Nome do grupo": ["Inativo", "Ativo"],
        "Risco Mês Atual Podicre": [100, 200],
        "Limite mês Atual Podicre": [100, 200],
    })
    base = normalize_base(df)
    out = aplicar_depara(base)
    # o cliente 30 (inativo) sai; o 31 fica
    assert "30" not in set(out["id"])
    assert "31" in set(out["id"])


def test_depara_vazio_nao_altera():
    from src.depara import aplicar_depara
    from src.raiox import normalize_base
    df = pd.DataFrame({"Nome do grupo": ["A"], "ID": [99],
                       "Risco Mês Atual Podicre": [1], "Limite mês Atual Podicre": [1]})
    base = normalize_base(df)
    out = aplicar_depara(base)  # sem de-para salvo p/ esse id -> igual
    assert len(out) == 1


def test_sim_nao_interpretacao():
    from src.depara import _sim_nao_para_int
    assert _sim_nao_para_int("Não") == 0
    assert _sim_nao_para_int("nao") == 0
    assert _sim_nao_para_int("Sim") == 1
    assert _sim_nao_para_int("") == 1
    assert _sim_nao_para_int(1) == 1
