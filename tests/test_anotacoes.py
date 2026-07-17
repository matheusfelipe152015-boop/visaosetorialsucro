"""Testa as funções de anotações (salvar, listar, editar, excluir)."""

from src.anotacoes import (
    atualizar_anotacao,
    criar_anotacao,
    excluir_anotacao,
    listar_anotacoes,
)


def test_criar_e_listar():
    aid = criar_anotacao("Título teste", "Conteúdo da anotação")
    df = listar_anotacoes()
    assert aid in set(df["id"])
    linha = df[df["id"] == aid].iloc[0]
    assert linha["titulo"] == "Título teste"
    assert linha["conteudo"] == "Conteúdo da anotação"


def test_atualizar():
    aid = criar_anotacao("Original", "texto original")
    atualizar_anotacao(aid, "Editado", "texto novo")
    df = listar_anotacoes()
    linha = df[df["id"] == aid].iloc[0]
    assert linha["titulo"] == "Editado"
    assert linha["conteudo"] == "texto novo"


def test_excluir():
    aid = criar_anotacao("Para excluir", "some")
    assert aid in set(listar_anotacoes()["id"])
    excluir_anotacao(aid)
    assert aid not in set(listar_anotacoes()["id"])


def test_ordena_recentes_primeiro():
    a1 = criar_anotacao("primeira", "a")
    a2 = criar_anotacao("segunda", "b")
    ids = list(listar_anotacoes()["id"])
    # a segunda (mais recente) vem antes da primeira
    assert ids.index(a2) < ids.index(a1)
