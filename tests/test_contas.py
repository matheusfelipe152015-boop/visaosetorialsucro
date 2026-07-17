"""Testa contas: cadastro, login, aprovação e regras de permissão."""


import pytest


@pytest.fixture(autouse=True)
def _limpa(monkeypatch):
    # define o email do ADM para os testes
    monkeypatch.setenv("ADMIN_EMAIL", "chefe@empresa.com")
    from sqlalchemy import text

    from src.persistence.db import get_engine
    with get_engine().begin() as c:
        c.execute(text("DELETE FROM usuarios"))
    yield


def test_senha_fraca_recusada():
    from src.contas import cadastrar
    ok, _ = cadastrar("a@b.com", "Ana", "123")       # curta
    assert not ok
    ok, _ = cadastrar("a@b.com", "Ana", "abcdefgh")  # sem número
    assert not ok


def test_email_invalido_recusado():
    from src.contas import cadastrar
    ok, _ = cadastrar("sem-arroba", "X", "Senha123")
    assert not ok


def test_cadastro_comum_fica_pendente():
    from src.contas import autenticar, cadastrar
    ok, _ = cadastrar("ana@empresa.com", "Ana", "Senha123")
    assert ok
    # não consegue entrar enquanto pendente
    u, _ = autenticar("ana@empresa.com", "Senha123")
    assert u is None


def test_email_do_cofre_vira_adm_ativo():
    from src.contas import autenticar, cadastrar
    ok, _ = cadastrar("chefe@empresa.com", "Chefe", "Senha123")
    assert ok
    u, _ = autenticar("chefe@empresa.com", "Senha123")
    assert u is not None
    assert u["papel"] == "adm"


def test_senha_errada_nao_entra():
    from src.contas import autenticar, cadastrar
    cadastrar("chefe@empresa.com", "Chefe", "Senha123")
    u, _ = autenticar("chefe@empresa.com", "OutraSenha9")
    assert u is None


def test_gerencia_nao_cria_adm():
    from src.contas import papeis_que_pode_conceder
    assert "adm" not in papeis_que_pode_conceder("gerencia")
    assert "adm" in papeis_que_pode_conceder("adm")


def test_analista_nao_concede_nada():
    from src.contas import papeis_que_pode_conceder
    assert papeis_que_pode_conceder("analista") == []


def test_fluxo_aprovacao():
    from src.contas import aprovar, autenticar, cadastrar, listar_usuarios
    cadastrar("chefe@empresa.com", "Chefe", "Senha123")
    adm, _ = autenticar("chefe@empresa.com", "Senha123")
    cadastrar("novo@empresa.com", "Novo", "Senha123")
    uid = listar_usuarios().query("email=='novo@empresa.com'").iloc[0]["id"]
    ok, _ = aprovar(uid, "analista", adm)
    assert ok
    u, _ = autenticar("novo@empresa.com", "Senha123")
    assert u is not None and u["papel"] == "analista"


def test_gerencia_nao_aprova_como_adm():
    from src.contas import aprovar
    gerente = {"id": "g1", "email": "g@e.com", "papel": "gerencia"}
    ok, _ = aprovar("qualquer", "adm", gerente)
    assert not ok  # gerência não pode conceder adm


def test_nao_revoga_a_si_mesmo():
    from src.contas import revogar
    adm = {"id": "a1", "email": "a@e.com", "papel": "adm"}
    ok, _ = revogar("a1", adm)
    assert not ok
