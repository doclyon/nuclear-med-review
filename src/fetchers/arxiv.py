"""Fetcher arXiv via son API REST (format Atom)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import httpx

from ..models import Article

log = logging.getLogger("revue.arxiv")

ARXIV_API = "http://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# arXiv demande un delai entre requetes : 1 req / 3s
_RATE = asyncio.Semaphore(1)


def _matches_filter(text: str, terms: list[str]) -> bool:
    """Verifie la presence d'au moins un terme (case-insensitive)."""
    t = text.lower()
    return any(term.lower() in t for term in terms)


async def _fetch_category(
    client: httpx.AsyncClient,
    category: str,
    window_hours: int,
    max_results: int,
) -> list[Article]:
    """Interroge une categorie arXiv, retourne les articles recents."""
    params = {
        "search_query": f"cat:{category}",
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    async with _RATE:
        await asyncio.sleep(3)  # delai impose par arXiv
        try:
            r = await client.get(ARXIV_API, params=params, timeout=30.0)
            r.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("arXiv %s indisponible : %s", category, e)
            return []

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as e:
        log.error("arXiv %s : parsing XML echoue (%s)", category, e)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    articles: list[Article] = []
    for entry in root.findall("atom:entry", NS):
        pub_str = entry.findtext("atom:published", default="", namespaces=NS)
        try:
            pub = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except ValueError:
            pub = None

        if pub and pub < cutoff:
            continue

        title = (entry.findtext("atom:title", default="", namespaces=NS) or "").strip()
        abstract = (entry.findtext("atom:summary", default="", namespaces=NS) or "").strip()

        # arxiv_id = dernier segment de l'URL
        arxiv_url = entry.findtext("atom:id", default="", namespaces=NS)
        arxiv_id = arxiv_url.rsplit("/", 1)[-1] if arxiv_url else None

        authors: list[str] = []
        for au in entry.findall("atom:author", NS):
            name = au.findtext("atom:name", default="", namespaces=NS)
            if name:
                authors.append(name)

        # DOI optionnel
        doi = entry.findtext("arxiv:doi", default=None, namespaces=NS)

        articles.append(
            Article(
                source="arxiv",
                source_name=f"arXiv ({category})",
                arxiv_id=arxiv_id,
                doi=doi,
                url=arxiv_url,
                title=title,
                abstract=abstract,
                authors=authors,
                journal="arXiv preprint",
                published_at=pub,
            )
        )

    log.info("arXiv %s : %d entrees recentes", category, len(articles))
    return articles


async def fetch_arxiv(
    categories: list[str],
    relevance_filter: list[str],
    window_hours: int = 48,
    max_results: int = 100,
) -> list[Article]:
    """Interroge les categories arXiv, applique le filtre de pertinence."""
    async with httpx.AsyncClient() as client:
        all_articles: list[Article] = []
        # Sequentiel pour respecter le rate limit arXiv (1/3s)
        for cat in categories:
            all_articles.extend(
                await _fetch_category(client, cat, window_hours, max_results)
            )

    filtered = [
        a for a in all_articles
        if _matches_filter(f"{a.title} {a.abstract}", relevance_filter)
    ]
    log.info("arXiv total : %d -> %d apres filtre de pertinence",
             len(all_articles), len(filtered))
    return filtered
