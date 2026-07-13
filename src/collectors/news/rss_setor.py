"""Coletor de noticias por RSS — radar de manchetes do setor.

Le os feeds dos portais, filtra o que e do setor, detecta empresa/tema no
titulo e grava TITULO + LINK + DATA. Nao copia o texto das materias (isso
seria republicacao); a plataforma leva voce a fonte.
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

FEEDS = [
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
    ("noticiasagricolas", "Noticias Agricolas", [
        "https://www.noticiasagricolas.com.br/rss/noticias/sucroenergetico.xml",
        "https://www.noticiasagricolas.com.br/rss/sucroenergetico.xml",
        "https://www.noticiasagricolas.com.br/feed",
    ]),
    ("udop", "UDOP", [
        "https://www.udop.com.br/rss/noticias.xml",
        "https://www.udop.com.br/feed/",
    ]),
]

PALAVRAS_SETOR = (
    "cana", "a\u00e7\u00facar", "acucar", "etanol", "sucroenerg", "usina", "biocombust",
    "cbio", "renovabio", "moagem", "atr", "biometano", "hidratado", "anidro",
    "safra", "canavi", "bioeletric", "sucroalcool",
)

EMPRESAS_NO_TITULO = {
    "ra\u00edzen": "raizen", "raizen": "raizen",
    "s\u00e3o martinho": "sao_martinho", "sao martinho": "sao_martinho",
    "jalles": "jalles",
    "adecoagro": "adecoagro",
    "cosan": "cosan",
    "ctc": "ctc",
}

TEMAS_NO_TITULO = {
    "produ\u00e7\u00e3o": "producao_safra", "producao": "producao_safra",
    "safra": "producao_safra", "moagem": "producao_safra", "colheita": "producao_safra",
    "cbio": "renovabio", "renovabio": "renovabio",
    "anp": "regulacao", "regula\u00e7": "regulacao", "lei": "regulacao", "mistura": "regulacao",
    "cra": "captacoes", "deb\u00eanture": "captacoes", "emiss\u00e3o": "captacoes",
    "capta\u00e7": "captacoes", "ipo": "captacoes",
    "exporta": "comex", "importa": "comex", "embarque": "comex",
    "biometano": "biometano", "biog\u00e1s": "biometano", "biogas": "biometano",
}


def _texto(el, *nomes):
    for n in nomes:
        achado = el.find(n)
        if achado is not None:
            if achado.text:
                return achado.text.strip()
            href = achado.get("href")
            if href:
                return href.strip()
    return ""


def _data(txt):
    if not txt:
        return None
    try:
        return parsedate_to_datetime(txt).date()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).date()
    except ValueError:
        return None


PALAVRAS_RUIDO = (
    "vaga", "emprego", "contrata", "curr\u00edculo", "curriculo", "sele\u00e7\u00e3o", "seletivo",
    "concurso", "est\u00e1gio", "estagio", "trainee", "sal\u00e1rio", "salario",
    "carreata", "sorteio", "promo\u00e7\u00e3o", "promocao", "curso", "inscri\u00e7", "inscric",
    "webinar", "palestra", "anivers\u00e1rio", "aniversario", "homenage",
    "receita de", "como fazer", "hor\u00f3scopo", "novela",
)


def _ruido(titulo):
    t = titulo.lower()
    return any(p in t for p in PALAVRAS_RUIDO)


def _relevante(titulo):
    """Do setor se cita tema OU uma empresa acompanhada.

    Sem a 2a regra, 'Sao Martinho emite CRA' seria descartada — e e justamente
    o tipo de noticia que interessa para credito.
    """
    if _ruido(titulo):
        return False
    t = titulo.lower()
    if any(p in t for p in PALAVRAS_SETOR):
        return True
    return any(termo in t for termo in EMPRESAS_NO_TITULO)


def parse_feed(xml_bytes, source_code):
    """Extrai as manchetes de um feed RSS ou Atom."""
    try:
        raiz = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    artigos = []
    for it in raiz.iter("item"):
        titulo = _texto(it, "title")
        link = _texto(it, "link", "guid")
        if not titulo or not link or not _relevante(titulo):
            continue
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


def detecta_empresas(titulo):
    t = titulo.lower()
    return sorted({code for termo, code in EMPRESAS_NO_TITULO.items() if termo in t})


def detecta_temas(titulo):
    t = titulo.lower()
    return sorted({code for termo, code in TEMAS_NO_TITULO.items() if termo in t})


def upsert_noticias(artigos):
    """Grava as noticias (idempotente pela url) + mencoes e temas."""
    eng = get_engine()
    agora = datetime.utcnow()
    novos = 0
    with eng.begin() as conn:
        topicos_ok = {r[0] for r in conn.execute(text("SELECT code FROM news_topics"))}
        empresas_ok = {r[0] for r in conn.execute(text("SELECT code FROM companies"))}
        for a in artigos:
            url = a["url"]
            existe = conn.execute(
                text("SELECT id FROM news_articles WHERE url_canonica = :u"), {"u": url}
            ).first()
            if existe:
                continue
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

    def collect(self):
        artigos = []
        for code, nome, urls in FEEDS:
            achou = False
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
                        achou = True
                        break
                except Exception:
                    continue
            if not achou:
                print(f"  {nome}: nenhum feed respondeu")
        return artigos

    def run(self):
        started = datetime.utcnow()
        try:
            artigos = self.collect()
            novos = upsert_noticias(artigos)
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), rows_seen=len(artigos),
                rows_new=novos, ok=True,
            )
        except Exception as exc:
            result = CollectorResult(
                source_code=self.source_code, started_at=started,
                finished_at=datetime.utcnow(), ok=False,
                error=f"{type(exc).__name__}: {exc}",
            )
        log_run(result)
        return result


_GN = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-150"
BUSCAS_GOOGLE = [
    "usina+de+cana+OR+etanol+OR+a\u00e7\u00facar+OR+sucroenerg\u00e9tico",
    "Ra\u00edzen+OR+%22S\u00e3o+Martinho%22+OR+%22Jalles+Machado%22+OR+Adecoagro+OR+Cosan+usina",
]
FEEDS += [("google_news", "Google Noticias", [_GN.format(q=q)]) for q in BUSCAS_GOOGLE]
