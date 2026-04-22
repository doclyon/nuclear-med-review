"""Fetcher des flux RSS via feedparser (execute en thread pool)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import httpx

from ..models import Article

log = logging.getLogger("revue.rss")


def _coerce_date(entry: dict) -> datetime | None:
    """Extrait la date d'une entree RSS, format variable."""
    for key in ("published", "updated", "created"):
        val = entry.get(key)
        if not val:
            continue
        try:
            dt = parsedate_to_datetime(val)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (TypeError, ValueError):
            continue
    # parsed struct_time
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
    return None


def _extract_doi(entry: dict) -> str | None:
    """Heuristique pour extraire un DOI depuis un lien ou id."""
    for key in ("link", "id"):
        val = entry.get(key, "")
        if "doi.org/" in val:
            return val.split("doi.org/", 1)[1].strip()
        if val.startswith("doi:"):
            return val[4:].strip()
    return None


async def _fetch_one(
    client: httpx.AsyncClient, name: str, url: str
) -> list[Article]:
    """Telecharge un flux, le parse dans un thread, retourne les articles."""
    try:
        r = await client.get(
            url,
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": "nuclear-med-review/1.0"},
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("RSS %s indisponible : %s", name, e)
        return []

    # feedparser est sync : on l'execute dans un thread
    parsed = await asyncio.to_thread(feedparser.parse, r.content)
    if parsed.bozo and not parsed.entries:
        log.warning("RSS %s : flux mal forme (%s)", name, parsed.bozo_exception)
        return []

    # On ne garde que les entrees recentes (< 72h)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
    articles: list[Article] = []
    for entry in parsed.entries:
        pub = _coerce_date(entry)
        if pub and pub < cutoff:
            continue
        title = (entry.get("title") or "").strip()
        if not title:
            continue
        # Abstract / resume
        abstract = entry.get("summary", "") or entry.get("description", "")
        # Auteurs
        authors_raw = entry.get("authors", [])
        authors = [a.get("name", "") for a in authors_raw if a.get("name")]
        if not authors and entry.get("author"):
            authors = [entry["author"]]

        articles.append(
            Article(
                source="rss",
                source_name=name,
                doi=_extract_doi(entry),
                url=entry.get("link"),
                title=title,
                abstract=abstract,
                authors=authors,
                journal=name,
                published_at=pub,
            )
        )
    log.info("RSS %s : %d entrees", name, len(articles))
    return articles


async def fetch_all_rss(feeds: list[dict]) -> list[Article]:
    """Interroge tous les flux RSS en parallele."""
    async with httpx.AsyncClient() as client:
        tasks = [_fetch_one(client, f["name"], f["url"]) for f in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    articles: list[Article] = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            log.error("RSS %s : exception %s", feeds[i]["name"], res)
        else:
            articles.extend(res)
    return articles
