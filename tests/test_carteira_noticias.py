"""Testa o cruzamento de clientes da carteira com manchetes."""

import pandas as pd

from src.carteira_noticias import casar_carteira, normalizar, variantes_do_nome


def test_normalizar_tira_acento_e_pontuacao():
    assert normalizar("São Martinho S.A.") == "SAO MARTINHO S A"


def test_variantes_remove_sufixo_societario():
    assert variantes_do_nome("DESTILARIA AGUA BONITA LTDA") == [
        "DESTILARIA AGUA BONITA", "AGUA BONITA"]


def test_variantes_ignora_nome_generico():
    assert variantes_do_nome("USINA") == []
    assert variantes_do_nome("AGRO") == []


def _clientes(pares):
    return pd.DataFrame([
        {"id_cliente": i, "grupo": g, "variantes": variantes_do_nome(g)}
        for i, g in pares
    ])


def test_casa_nome_completo_e_apelido():
    artigos = pd.DataFrame([
        {"id": "a1", "titulo": "Cocal anuncia investimento em etanol", "resumo": ""},
        {"id": "a2", "titulo": "Preço do açúcar sobe na ICE", "resumo": ""},
    ])
    achados = casar_carteira(artigos, _clientes([("1", "USINA COCAL")]))
    assert list(achados["article_id"]) == ["a1"]
    assert achados.iloc[0]["grupo"] == "USINA COCAL"


def test_nao_casa_dentro_de_outra_palavra():
    """'ADM' não pode casar dentro de 'administração'."""
    artigos = pd.DataFrame([
        {"id": "a1", "titulo": "Nova administração da cooperativa", "resumo": ""},
    ])
    achados = casar_carteira(artigos, _clientes([("1", "ADM")]))
    assert achados.empty


def test_casa_no_resumo_tambem():
    artigos = pd.DataFrame([
        {"id": "a1", "titulo": "Balanço do setor", "resumo": "A Jalles Machado informou"},
    ])
    achados = casar_carteira(artigos, _clientes([("1", "JALLES MACHADO")]))
    assert len(achados) == 1


def test_um_cliente_uma_vez_por_noticia():
    artigos = pd.DataFrame([
        {"id": "a1", "titulo": "Usina Cocal e Cocal fecham acordo", "resumo": "Cocal"},
    ])
    achados = casar_carteira(artigos, _clientes([("1", "USINA COCAL")]))
    assert len(achados) == 1


def test_sem_artigos_devolve_vazio():
    assert casar_carteira(pd.DataFrame(), _clientes([("1", "X")])).empty
