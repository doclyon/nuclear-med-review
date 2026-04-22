"""Fetcher medRxiv via son API publique (api.biorxiv.org)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx

from ..models import Article

log = logging.getLogger("revue.medrxiv")

MEDRXIV_API = "https://api.biorxiv.org/details/medrxiv"


async def fetch_medrxiv(
    subjects: list[str],
    window_hours: int = 36,
) -> list[Article]:
    """Interroge l'API medRxiv (fenetre de dates) puis filtre par sujet."""
    now = datetime.now(timezone.utc)
    # API attend YYYY-MM-DD, on prend 3 jours pour couvrir la latence
    since = (now - timedelta(hours=max(window_hours, 72))).strftime("%Y-%m-%d")
    until = now.strftime("%Y-%m-%d")
    url = f"{MEDRXIV_API}/{since}/{until}/0"

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, timeout=30.0)
            r.raise_for_status()
            data = r.json()
        except (httpx.HTTPError, ValueError) as e:
            log.warning("medRxiv indisponible : %s", e)
            return []

    collection = data.get("collection", [])
    subjects_lc = {s.lower() for s in subjects}

    articles: list[Article] = []
    for entry in collection:
        cat = (entry.get("category") or "").lower().replace(" ", "-")
        if not any(s in cat for s in subjects_lc):
            continue

        doi = entry.get("doi") or None
        title = (entry.get("title") or "").strip()
        abstract = (entry.get("abstract") or "").strip()
        authors_str = entry.get("authors", "")
        authors = [a.strip() for a in authors_str.split(";") if a.strip()]

        pub_str = entry.get("date", "")
        try:
            pub = datetime.strptime(pub_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pub = None

        url_article = f"https://www.medrxiv.org/content/{doi}" if doi else None

        articles.append(
            Article(
                source="medrxiv",
                source_name="medRxiv",
                doi=doi,
                url=url_article,
                title=title,
                abstract=abstract,
                authors=authors,
                first_affiliation=entry.get("author_corresponding_institution"),
                journal=f"medRxiv ({entry.get('category', '')})",
                published_at=pub,
            )
        )

    log.info("medRxiv : %d preprints pertinents", len(articles))
    return articles
