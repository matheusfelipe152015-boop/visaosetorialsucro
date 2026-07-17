"""Testa o núcleo do Raio X: normalização, PD e comentários por ID."""

import pandas as pd


def test_normaliza_planilha_simples():
    from src.raiox import normalize_base
    # planilha com nomes "reais" que o Raio X reconhece
    df = pd.DataFrame({
        "ID": [101, 102],
        "Nome do grupo": ["Grupo A", "Grupo B"],
        "Risco Mês Atual Podicre": [1000, 2000],
        "Limite mês Atual Podicre": [1500, 2500],
        "Rating Mês Atual Podicre": ["Ba1", "B2"],
    })
    out = normalize_base(df)
    assert "grupo" in out.columns
    assert out["risco"].sum() == 3000
    assert out["rating_num"].iloc[0] == 4   # Ba1 -> 4
    assert out["bucket_rating"].iloc[0] == "Ba1 - Ba4"


def test_disponibilidade_calculada():
    from src.raiox import normalize_base
    df = pd.DataFrame({
        "Nome do grupo": ["X"], "Risco Mês Atual Podicre": [400],
        "Limite mês Atual Podicre": [1000],
    })
    out = normalize_base(df)
    assert out["disponibilidade"].iloc[0] == 600


def test_sem_grupo_da_erro():
    from src.raiox import normalize_base
    df = pd.DataFrame({"Risco Mês Atual Podicre": [1]})
    try:
        normalize_base(df)
        raise AssertionError("deveria ter dado erro")
    except ValueError:
        pass


def test_pd_media_ponderada():
    from src.raiox import calcular_pd_e_rating_medio, normalize_base
    df = pd.DataFrame({
        "Nome do grupo": ["A", "B"],
        "Risco Mês Atual Podicre": [1000, 1000],
        "Rating Mês Atual Podicre": ["A1", "A1"],
    })
    out = normalize_base(df)
    pd_media, rating = calcular_pd_e_rating_medio(out)
    assert pd_media is not None
    assert rating == "A1"   # tudo A1 -> média A1


def test_comentario_persiste_por_id():
    from src.raiox import aplicar_comentarios, normalize_base, salvar_comentario
    # salva um comentário para o cliente 555
    salvar_comentario("555", "Acompanhar", "Cliente renegociou", "tester")
    # sobe uma "carteira" com esse cliente
    df = pd.DataFrame({
        "ID": [555, 556], "Nome do grupo": ["Fulano", "Beltrano"],
        "Risco Mês Atual Podicre": [10, 20],
        "Limite mês Atual Podicre": [10, 20],
    })
    base = normalize_base(df)
    com = aplicar_comentarios(base)
    linha = com[com["id"] == "555"].iloc[0]
    assert linha["comentario"] == "Cliente renegociou"
    assert linha["status"] == "Acompanhar"
    # o outro cliente fica sem comentário
    assert com[com["id"] == "556"].iloc[0]["comentario"] == ""


def test_comentario_atualiza():
    from src.raiox import carregar_comentarios, salvar_comentario
    salvar_comentario("999", "Ok", "primeiro", "t")
    salvar_comentario("999", "Revisar", "segundo", "t")
    c = carregar_comentarios()
    linha = c[c["id_cliente"] == "999"].iloc[0]
    assert linha["comentario"] == "segundo"
    assert linha["status"] == "Revisar"


# ── robustez: planilhas problemáticas não podem quebrar ───────────────────

def test_limite_zero_nao_quebra():
    from src.raiox import normalize_base
    df = pd.DataFrame({"Nome do grupo": ["X"], "Risco Mês Atual Podicre": [100],
                       "Limite mês Atual Podicre": [0]})
    out = normalize_base(df)  # não pode estourar divisão por zero
    assert len(out) == 1


def test_rating_invalido_nao_quebra():
    from src.raiox import calcular_pd_e_rating_medio, normalize_base
    df = pd.DataFrame({"Nome do grupo": ["X", "Y"],
                       "Risco Mês Atual Podicre": [100, 200],
                       "Rating Mês Atual Podicre": ["XYZ", ""]})
    out = normalize_base(df)
    pd_m, r = calcular_pd_e_rating_medio(out)  # não pode estourar
    assert r == "-"


def test_numeros_como_texto_nao_quebra():
    from src.raiox import normalize_base
    df = pd.DataFrame({"Nome do grupo": ["X"], "Risco Mês Atual Podicre": ["abc"],
                       "Limite mês Atual Podicre": ["xyz"]})
    out = normalize_base(df)  # vira NaN, não quebra
    assert len(out) == 1


def test_planilha_vazia_nao_quebra():
    from src.raiox import normalize_base
    df = pd.DataFrame({"Nome do grupo": []})
    out = normalize_base(df)
    assert len(out) == 0
