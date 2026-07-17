"""Coletor de notícias por RSS — radar de manchetes do setor.

O que faz: lê os feeds RSS dos portais do setor, filtra o que é relevante
(cana, açúcar, etanol, usinas...), detecta empresa e tema mencionados no título,
e grava título + link + data.

O que NÃO faz (de propósito): não copia o texto das matérias. RSS entrega
manchete e link; reproduzir o conteúdo dos veículos seria republicação. A
plataforma funciona como radar: mostra o que saiu e leva você à fonte.

Feeds: como cada portal usa um caminho diferente (e alguns mudam), tentamos
uma lista de candidatos por veículo e usamos o primeiro que responder.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import text

from src.domain.models import CollectorResult
from src.persistence.db import get_engine
from src.persistence.repositories import log_run

SOURCE_CODE = "rss"

# (código da fonte na plataforma, nome, [urls candidatas de feed])
# (code da fonte, nome, urls candidatas). Nem todo portal publica RSS — os que
# não responderem são simplesmente pulados (o coletor não falha por isso).
FEEDS: list[tuple[str, str, list[str]]] = [
    ("jornalcana", "JornalCana", [
        "https://jornalcana.com.br/feed/",
        "https://jornalcana.com.br/feed",
    ]),
    ("novaCana", "novaCana", [
        "https://www.novacana.com/rss/noticias",
        "https://www.novacana.com/feed/",
        "https://www.novacana.com/rss.xml",
        "https://www.novacana.com/noticias/feed/",
    ]),
    ("epbr", "epbr", [
        "https://epbr.com.br/feed/",
        "https://epbr.com.br/categoria/biocombustiveis/feed/",
    ]),
    ("noticiasagricolas", "Notícias Agrícolas", [
        "https://www.noticiasagricolas.com.br/rss/noticias/sucroenergetico.xml",
        "https://www.noticiasagricolas.com.br/rss/sucroenergetico.xml",
        "https://www.noticiasagricolas.com.br/feed",
    ]),
    ("udop", "UDOP", [
        "https://www.udop.com.br/rss/noticias.xml",
        "https://www.udop.com.br/feed/",
    ]),
]

# Google Notícias: feed público de busca. Cobre dezenas de veículos (inclusive os
# que não têm RSS próprio). O link passa pelo Google e redireciona para a fonte.
_GN = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-150"
BUSCAS_GOOGLE = [
    "usina+de+cana+OR+etanol+OR+açúcar+OR+sucroenergético",
    "Raízen+OR+%22São+Martinho%22+OR+%22Jalles+Machado%22+OR+Adecoagro+OR+Cosan+usina",
]
FEEDS += [("google_news", "Google Notícias", [_GN.format(q=q)]) for q in BUSCAS_GOOGLE]

# Só interessa o que é do setor (feeds gerais trazem muita coisa de fora).
PALAVRAS_SETOR = (
    "cana", "açúcar", "acucar", "etanol", "sucroenerg", "usina", "biocombust",
    "cbio", "renovabio", "moagem", "atr", "biometano", "hidratado", "anidro",
    "safra", "canavi", "bioeletric", "sucroalcool",
)

# empresa mencionada no título -> code da empresa na plataforma
EMPRESAS_NO_TITULO = {
    "raízen": "raizen", "raizen": "raizen",
    "são martinho": "sao_martinho", "sao martinho": "sao_martinho",
    "jalles": "jalles",
    "adecoagro": "adecoagro",
    "cosan": "cosan",
    "ctc": "ctc",
}

# tema mencionado -> code do tópico (precisa existir em news_topics)
TEMAS_NO_TITULO = {
    "produção": "producao_safra", "producao": "producao_safra",
    "safra": "producao_safra", "moagem": "producao_safra", "colheita": "producao_safra",
    "cbio": "renovabio", "renovabio": "renovabio",
    "anp": "regulacao", "regulaç": "regulacao", "lei": "regulacao", "mistura": "regulacao",
    "cra": "captacoes", "debênture": "captacoes", "emissão": "captacoes",
    "captaç": "captacoes", "ipo": "captacoes",
    "exporta": "comex", "importa": "comex", "embarque": "comex",
    "biometano": "biometano", "biogás": "biometano", "biogas": "biometano",
}


def _texto(el, *nomes: str) -> str:
    """Primeiro dos nomes que existir no elemento (trata namespaces do Atom)."""
    for n in nomes:
        achado = el.find(n)
        if achado is not None:
            if achado.text:
                return achado.text.strip()
            href = achado.get("href")  # Atom usa <link href="...">
            if href:
                return href.strip()
    return ""


def _data(txt: str) -> date | None:
    if not txt:
        return None
    try:  # RSS: "Fri, 10 Jul 2026 14:03:00 -0300"
        return parsedate_to_datetime(txt).date()
    except (TypeError, ValueError):
        pass
    try:  # Atom: "2026-07-10T14:03:00Z"
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).date()
    except ValueError:
        return None


# Ruído: assuntos que citam o setor mas não servem para inteligência de mercado
# (o Google Notícias traz de tudo — vagas, eventos, promoções).
PALAVRAS_RUIDO = (
    "vaga", "emprego", "contrata", "currículo", "curriculo", "seleção", "seletivo",
    "concurso", "estágio", "estagio", "trainee", "salário", "salario",
    "carreata", "sorteio", "promoção", "promocao", "curso", "inscriç", "inscric",
    "webinar", "palestra", "aniversário", "aniversario", "homenage",
    "receita de", "como fazer", "horóscopo", "novela",
)


def _ruido(titulo: str) -> bool:
    t = titulo.lower()
    return any(p in t for p in PALAVRAS_RUIDO)


def _relevante(titulo: str) -> bool:
    """Do setor se cita tema OU uma empresa acompanhada.

    Sem a segunda regra, 'São Martinho emite CRA de R$ 1,2 bi' seria descartada
    (não tem 'cana'/'etanol' no título) — e é justamente o tipo de notícia que
    interessa para crédito.
    """
    if _ruido(titulo):
        return False  # vaga de emprego, evento, curso... não é inteligência
    t = titulo.lower()
    if any(p in t for p in PALAVRAS_SETOR):
        return True
    return any(termo in t for termo in EMPRESAS_NO_TITULO)


def parse_feed(xml_bytes: bytes, source_code: str) -> list[dict]:
    """Extrai as manchetes de um feed RSS ou Atom."""
    try:
        raiz = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    itens = raiz.iter("item")  # RSS 2.0
    artigos: list[dict] = []
    for it in itens:
        titulo = _texto(it, "title")
        link = _texto(it, "link", "guid")
        if not titulo or not link or not _relevante(titulo):
            continue
        # O Google Notícias formata o título como "Título - Veículo".
        veiculo = _texto(it, "source")
        if veiculo and titulo.endswith(f" - {veiculo}"):
            titulo = titulo[: -len(f" - {veiculo}")]
        artigos.append({
            "titulo": re.sub(r"\s+", " ", titulo).strip(),
            "url": link,
            "data": _data(_texto(it, "pubDate", "date")),
            "source_code": source_code,
            "veiculo": veiculo or None,
        })
    if artigos:
        return artigos
    # Atom (usa namespace)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for e in raiz.findall("a:entry", ns):
        titulo = _texto(e, "a:title")
        link_el = e.find("a:link", ns)
        link = link_el.get("href") if link_el is not None else ""
        if not titulo or not link or not _relevante(titulo):
            continue
        artigos.append({
            "titulo": re.sub(r"\s+", " ", titulo).strip(),
            "url": link,
            "data": _data(_texto(e, "a:published", "a:updated")),
            "source_code": source_code,
            "veiculo": None,
        })
    return artigos


def detecta_empresas(titulo: str) -> list[str]:
    t = titulo.lower()
    return sorted({code for termo, code in EMPRESAS_NO_TITULO.items() if termo in t})


def detecta_temas(titulo: str) -> list[str]:
    t = titulo.lower()
    return sorted({code for termo, code in TEMAS_NO_TITULO.items() if termo in t})


def upsert_noticias(artigos: list[dict]) -> int:
    """Grava as notícias (idempotente pela url) + menções e temas."""
    eng = get_engine()
    agora = datetime.utcnow()
    novos = 0
    with eng.begin() as conn:
        # tópicos existentes (para não violar chave estrangeira)
        topicos_ok = {r[0] for r in conn.execute(text("SELECT code FROM news_topics"))}
        empresas_ok = {r[0] for r in conn.execute(text("SELECT code FROM companies"))}
        for a in artigos:
            url = a["url"]
            existe = conn.execute(
                text("SELECT id FROM news_articles WHERE url_canonica = :u"), {"u": url}
            ).first()
            if existe:
                continue  # já temos esta notícia
            aid = uuid.uuid4().hex
            h = hashlib.sha256(url.encode()).hexdigest()[:32]
            conn.execute(
                text("""INSERT INTO news_articles
                        (id, source_code, titulo, resumo, url_original, url_canonica,
                         data_publicacao, data_coleta, idioma, pais, hash, status_coleta)
                        VALUES(:id,:src,:t,:res,:u,:u,:dp,:dc,'pt','BR',:h,'ok')"""),
                {"id": aid, "src": a["source_code"], "t": a["titulo"],
                 "res": a.get("veiculo"), "u": url,
                 "dp": a["data"], "dc": agora, "h": h},
            )
            novos += 1
            for code in detecta_empresas(a["titulo"]):
                if code in empresas_ok:
                    conn.execute(
                        text("INSERT INTO article_company_mentions(article_id, company_code) "
                             "VALUES(:a,:c)"),
                        {"a": aid, "c": code},
                    )
            for code in detecta_temas(a["titulo"]):
                if code in topicos_ok:
                    conn.execute(
                        text("INSERT INTO article_topics(article_id, topic_code) VALUES(:a,:t)"),
                        {"a": aid, "t": code},
                    )
    return novos


class RssNoticiasCollector:
    source_code = SOURCE_CODE
    version = "0.1.0"

    def collect(self) -> list[dict]:
        artigos: list[dict] = []
        for code, nome, urls in FEEDS:
            for url in urls:
                try:
                    resp = httpx.get(
                        url, timeout=12, follow_redirects=True,
                        headers={"User-Agent": "visaosetorialsucro/0.1 (radar-setorial)"},
                    )
                    resp.raise_for_status()
                    achados = parse_feed(resp.content, code)
                    if achados:
                        artigos.extend(achados)
                        print(f"  {nome}: {len(achados)} manchetes")
                        break  # este veículo respondeu; vai para o próximo
                except Exception:  # noqa: BLE001 — um feed fora do ar não derruba os outros
                    continue
            else:
                print(f"  {nome}: nenhum feed respondeu")
        return artigos

    def run(self) -> CollectorResult:
        started = datetime.utcnow()
        try:
            artigos = self.collect()
            novos = upsert_noticias(artigos)
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), rows_seen=len(artigos),
                rows_new=novos, ok=True,
            )
        except Exception as exc:  # noqa: BLE001
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        log_run(result)
        return result
