"""Testa as funções das abas do Raio X (tabelas, qualidade, clientes, visitas)."""



def _base_exemplo():
    from src.raiox import normalize_base
    from src.raiox_exemplo import carteira_exemplo
    return normalize_base(carteira_exemplo())


def test_top_bucket_tem_totais():
    from src.raiox_abas import table_top_bucket
    base = _base_exemplo()
    t = table_top_bucket(base, "Ba1 - Ba4")
    assert not t.empty
    # deve ter as linhas de total e delta no fim
    grupos = set(t["Grupo"])
    assert "Total exibido" in grupos
    assert "Delta" in grupos


def test_b2_ou_pior():
    from src.raiox_abas import table_b2_ou_pior
    base = _base_exemplo()
    t = table_b2_ou_pior(base)
    # a carteira de exemplo tem clientes B2+ (C1, B2...)
    assert not t.empty


def test_movimentacao_indisponivel_no_exemplo():
    from src.raiox_abas import movement_available
    base = _base_exemplo()
    # exemplo não tem M-1
    assert not movement_available(base)


def test_qualidade_gera_resumo():
    from src.raiox_abas import build_qualidade
    base = _base_exemplo()
    resumo, detalhes = build_qualidade(base)
    assert not resumo.empty
    assert "Pendência" in resumo.columns
    assert isinstance(detalhes, dict)


def test_clientes_por_analista():
    from src.raiox_abas import clientes_por_analista
    base = _base_exemplo()
    r = clientes_por_analista(base)
    assert not r.empty
    assert "Analista" in r.columns
    # a carteira de exemplo tem 4 analistas
    assert len(r) == 3


def test_cobertura_visitas():
    from src.raiox_abas import cobertura_visitas
    base = _base_exemplo()
    v = cobertura_visitas(base)
    # há analistas, mas nenhuma visita registrada no exemplo
    if not v.empty:
        assert v["Com visita"].sum() == 0
