"""Deduplication stricte (DOI/PMID) + fuzzy (titre) + memoire inter-runs."""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import date, datetime, timedelta
from pathlib import Path

from rapidfuzz import fuzz

from ..models import Article

log = logging.getLogger("revue.dedup")

# Historique inter-runs : N derniers jours de DOI/PMID deja traites.
HISTORY_WINDOW_DAYS = 7


def _normalize_title(t: str) -> str:
    """Normalise un titre pour le fuzzy matching."""
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = t.lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def deduplicate(articles: list[Article], threshold: int = 90) -> list[Article]:
    """Deduplique une liste d'articles (DOI strict + titre fuzzy).

    Pour les doublons fuzzy, on garde la version la plus 'riche' (abstract
    le plus long, source PubMed prioritaire).
    """
    seen_keys: dict[str, Article] = {}
    titles_kept: list[tuple[str, Article]] = []
    dups = 0

    for art in articles:
        key = art.unique_key()
        if key in seen_keys:
            # Doublon strict : garder celui avec l'abstract le plus long
            existing = seen_keys[key]
            if len(art.abstract) > len(existing.abstract):
                seen_keys[key] = art
                # Mettre a jour dans titles_kept aussi
                titles_kept = [
                    (_normalize_title(art.title), art) if a is existing else (t, a)
                    for t, a in titles_kept
                ]
            dups += 1
            continue

        norm = _normalize_title(art.title)
        if not norm:
            seen_keys[key] = art
            titles_kept.append((norm, art))
            continue

        # Fuzzy check
        fuzzy_match: Article | None = None
        for kept_norm, kept_art in titles_kept:
            if kept_norm and fuzz.ratio(norm, kept_norm) >= threshold:
                fuzzy_match = kept_art
                break

        if fuzzy_match is not None:
            dups += 1
            # Fusion : conserver l'article avec le plus d'info
            if _richness(art) > _richness(fuzzy_match):
                # Remplacer
                old_key = fuzzy_match.unique_key()
                seen_keys.pop(old_key, None)
                seen_keys[key] = art
                titles_kept = [
                    (norm, art) if a is fuzzy_match else (t, a)
                    for t, a in titles_kept
                ]
            continue

        seen_keys[key] = art
        titles_kept.append((norm, art))

    result = list(seen_keys.values())
    log.info("Dedup : %d articles -> %d uniques (%d doublons)",
             len(articles), len(result), dups)
    return result


def _richness(a: Article) -> int:
    """Score de richesse pour choisir entre deux doublons."""
    score = len(a.abstract)
    if a.source == "pubmed":
        score += 500  # on prefere PubMed car metadonnees propres
    if a.doi:
        score += 200
    if a.first_affiliation:
        score += 100
    return score


# ---------- Memoire inter-runs ----------

def load_history(path: Path) -> dict[str, str]:
    """Charge l'historique (cle article -> date ISO).

    Si le fichier n'existe pas, retourne un dict vide.
    """
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Impossible de lire l'historique %s : %s", path, e)
        return {}


def save_history(path: Path, history: dict[str, str]) -> None:
    """Sauvegarde l'historique en purgeant les entrees > HISTORY_WINDOW_DAYS."""
    cutoff = date.today() - timedelta(days=HISTORY_WINDOW_DAYS)
    pruned = {
        k: v for k, v in history.items()
        if datetime.fromisoformat(v).date() >= cutoff
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(pruned, f, ensure_ascii=False, indent=2, sort_keys=True)
    log.info("Historique sauvegarde : %d entrees (fenetre %d jours)",
             len(pruned), HISTORY_WINDOW_DAYS)


def filter_already_seen(
    articles: list[Article], history: dict[str, str]
) -> list[Article]:
    """Ecarte les articles deja presents dans l'historique."""
    today = date.today().isoformat()
    fresh: list[Article] = []
    for art in articles:
        k = art.unique_key()
        if k in history:
            continue
        fresh.append(art)
        history[k] = today
    log.info("Filtre historique : %d -> %d articles nouveaux",
             len(articles), len(fresh))
    return fresh
