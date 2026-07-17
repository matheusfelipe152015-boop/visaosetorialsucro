"""Testa o coletor de notícias por RSS (offline, feed de exemplo)."""

from datetime import date

from src.collectors.news.rss_setor import (
    detecta_empresas,
    detecta_temas,
    parse_feed,
)

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Portal do setor</title>
    <item>
      <title>Raizen eleva moagem de cana no Centro-Sul</title>
      <link>https://exemplo.com/raizen-moagem</link>
      <pubDate>Fri, 10 Jul 2026 14:03:00 -0300</pubDate>
    </item>
    <item>
      <title>Exportacoes de acucar batem recorde em junho</title>
      <link>https://exemplo.com/exportacoes-acucar</link>
      <pubDate>Thu, 09 Jul 2026 09:00:00 -0300</pubDate>
    </item>
    <item>
      <title>Novo shopping abre em Sao Paulo</title>
      <link>https://exemplo.com/shopping</link>
      <pubDate>Thu, 09 Jul 2026 08:00:00 -0300</pubDate>
    </item>
  </channel>
</rss>"""


def test_extrai_manchetes_com_link():
    itens = parse_feed(RSS, "portal")
    assert len(itens) == 2  # o shopping (fora do setor) foi descartado
    primeiro = itens[0]
    assert primeiro["titulo"].startswith("Raizen eleva moagem")
    assert primeiro["url"] == "https://exemplo.com/raizen-moagem"
    assert primeiro["data"] == date(2026, 7, 10)
    assert primeiro["source_code"] == "portal"


def test_filtra_fora_do_setor():
    titulos = [i["titulo"] for i in parse_feed(RSS, "portal")]
    assert not any("shopping" in t.lower() for t in titulos)


def test_detecta_empresa_no_titulo():
    assert detecta_empresas("Raizen eleva moagem de cana") == ["raizen"]
    assert detecta_empresas("Sao Martinho e Cosan fecham acordo") == ["cosan", "sao_martinho"]
    assert detecta_empresas("Preco do etanol sobe") == []


def test_detecta_tema_no_titulo():
    assert "producao_safra" in detecta_temas("Usina eleva moagem na safra")
    assert "comex" in detecta_temas("Exportacoes de acucar batem recorde")
    assert "captacoes" in detecta_temas("Emissao de CRA de R$ 1 bi")


def test_feed_invalido_nao_quebra():
    assert parse_feed(b"isso nao e xml", "portal") == []


# ── formato do Google Notícias ────────────────────────────────────────────

RSS_GOOGLE = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Raizen eleva moagem no Centro-Sul - Valor Economico</title>
      <link>https://news.google.com/rss/articles/ABC123</link>
      <pubDate>Fri, 10 Jul 2026 14:03:00 -0300</pubDate>
      <source url="https://valor.globo.com">Valor Economico</source>
    </item>
  </channel>
</rss>"""


def test_google_limpa_titulo_e_guarda_veiculo():
    itens = parse_feed(RSS_GOOGLE, "google_news")
    assert len(itens) == 1
    # o " - Valor Economico" some do título e vira o veículo
    assert itens[0]["titulo"] == "Raizen eleva moagem no Centro-Sul"
    assert itens[0]["veiculo"] == "Valor Economico"
    assert itens[0]["url"].startswith("https://news.google.com")


def test_filtra_ruido_vagas_e_eventos():
    """Vaga de emprego cita a usina, mas não é inteligência de mercado."""
    from src.collectors.news.rss_setor import _relevante
    assert not _relevante("Vagas de emprego na Usina Sao Martinho")
    assert not _relevante("Raizen promove carreata em Brotas")
    assert not _relevante("Curso de capacitacao para operadores de usina")
    # o que importa continua entrando
    assert _relevante("Conselho discute mais etanol na gasolina")
    assert _relevante("Sao Martinho emite CRA de R$ 1,2 bilhao")
