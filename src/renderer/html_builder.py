"""Construction du HTML via Jinja2."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .. import __version__
from ..config import load_categories
from ..models import Article

log = logging.getLogger("revue.renderer")

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _group_by_category(articles: list[Article]) -> dict[str, list[Article]]:
    """Regroupe les articles par categorie, tri par score decroissant."""
    groups: dict[str, list[Article]] = defaultdict(list)
    for art in articles:
        groups[art.category_id or "general_medicine"].append(art)
    for cat_id in groups:
        groups[cat_id].sort(key=lambda a: (-a.relevance_score, a.title))
    return dict(groups)


def _estimate_reading_time(articles: list[Article]) -> int:
    """Estime le temps de lecture en minutes (250 mots/minute)."""
    total_words = 0
    for a in articles:
        for v in a.summary_fr.values():
            total_words += len((v or "").split())
        total_words += len((a.title_fr or a.title or "").split())
    return max(1, round(total_words / 250))


def _top_articles(articles: list[Article], n: int = 3) -> list[Article]:
    """Retourne les n articles les mieux notes."""
    return sorted(articles, key=lambda a: (-a.relevance_score, a.title))[:n]


def render_review(
    articles: list[Article],
    stats: dict[str, Any],
    output_path: Path,
) -> tuple[str, dict[str, Any]]:
    """Genere le HTML complet et l'ecrit sur disque.

    Retourne (html_string, meta) ou meta contient compteurs et top articles.
    """
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("review.html.j2")

    categories = load_categories()
    groups = _group_by_category(articles)
    counts = Counter({c["id"]: len(groups.get(c["id"], [])) for c in categories})
    # Categories non vides, dans l'ordre defini par le YAML
    active_categories = [c for c in categories if counts[c["id"]] > 0]

    top = _top_articles(articles, n=3)
    reading_time = _estimate_reading_time(articles)

    today = date.today()
    today_fr = today.strftime("%d/%m/%Y")

    meta = {
        "date": today.isoformat(),
        "date_fr": today_fr,
        "n_articles": len(articles),
        "n_scraped": stats.get("n_scraped", 0),
        "n_categories": len(active_categories),
        "reading_time": reading_time,
        "counts": dict(counts),
        "active_categories": active_categories,
        "top_articles": top,
        "stats": stats,
        "version": __version__,
    }

    html = template.render(
        articles=articles,
        groups=groups,
        categories=categories,
        active_categories=active_categories,
        counts=counts,
        top=top,
        meta=meta,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    log.info("HTML ecrit : %s (%d articles, %d rubriques actives)",
             output_path, len(articles), len(active_categories))
    return html, meta
