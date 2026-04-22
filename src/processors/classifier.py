"""Scoring initial par mots-cles et filtrage par seuil."""

from __future__ import annotations

import logging
import re

from ..models import Article

log = logging.getLogger("revue.classifier")


def _count_hits(text: str, terms: list[str]) -> int:
    """Compte les occurrences distinctes de termes dans le texte."""
    t = text.lower()
    hits = 0
    for term in terms:
        # Mot-entier ou inclusion simple selon qu'il contient un separateur
        pattern = re.escape(term.lower())
        if re.search(pattern, t):
            hits += 1
    return hits


def score_relevance(
    articles: list[Article],
    keywords_strong: list[str],
    keywords_context: list[str],
) -> list[Article]:
    """Calcule un score de pertinence par article (in-place).

    - 2 pts par mot-cle 'strong' present
    - 1 pt par mot-cle 'context' present
    """
    for art in articles:
        text = f"{art.title}\n{art.abstract}"
        strong = _count_hits(text, keywords_strong)
        ctx = _count_hits(text, keywords_context)
        art.keyword_score = 2 * strong + ctx
    return articles


def filter_by_threshold(
    articles: list[Article], threshold: float = 2.0
) -> tuple[list[Article], list[Article]]:
    """Separe les articles en (retenus, ambigus).

    - Retenus : score >= threshold
    - Ambigus : 1 <= score < threshold (arbitres ensuite par Claude)
    - Rejetes : score < 1 (ecartes silencieusement)
    """
    kept: list[Article] = []
    ambiguous: list[Article] = []
    rejected = 0
    for art in articles:
        if art.keyword_score >= threshold:
            kept.append(art)
        elif art.keyword_score >= 1:
            ambiguous.append(art)
        else:
            rejected += 1
    log.info(
        "Scoring : %d retenus, %d ambigus, %d ecartes",
        len(kept), len(ambiguous), rejected,
    )
    return kept, ambiguous
