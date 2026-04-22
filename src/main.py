"""Orchestration du pipeline quotidien de revue bibliographique.

Usage :
    python -m src.main              # execution complete (fetch + Claude + email)
    python -m src.main --dry-run    # genere le HTML mais n'envoie pas l'email
    python -m src.main --demo       # genere le HTML avec des donnees synthetiques
    python -m src.main --verbose    # logs DEBUG
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from . import __version__
from .config import categories_map, load_queries, load_sources
from .fetchers import fetch_all_rss, fetch_arxiv, fetch_medrxiv, fetch_pubmed
from .logging_setup import setup_logging
from .models import Article
from .notifier import send_email
from .processors import (
    deduplicate,
    enrich_with_claude,
    filter_already_seen,
    filter_by_threshold,
    load_history,
    save_history,
    score_relevance,
)
from .renderer import render_review

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
HISTORY_PATH = OUTPUT_DIR / "history.json"


async def fetch_all_sources(
    sources_cfg: dict, log: logging.Logger
) -> list[Article]:
    """Lance en parallele tous les fetchers, resilient aux pannes."""
    # Aplatir la liste des journaux PubMed
    journals: list[str] = []
    for group in sources_cfg["pubmed"].values():
        journals.extend(group)

    rss_feeds = sources_cfg.get("rss", [])
    arxiv_cfg = sources_cfg.get("arxiv", {})
    medrxiv_cfg = sources_cfg.get("medrxiv", {})
    window = sources_cfg.get("window_hours", 36)
    max_per_source = sources_cfg.get("max_articles_per_source", 200)

    log.info("Lancement des fetchers (fenetre %dh)", window)
    tasks = {
        "pubmed": fetch_pubmed(journals, window, max_per_source),
        "rss": fetch_all_rss(rss_feeds),
        "arxiv": fetch_arxiv(
            arxiv_cfg.get("categories", []),
            arxiv_cfg.get("relevance_filter", []),
            max(window, 48),  # arXiv a souvent peu de trafic en 24h
            max_per_source,
        ),
        "medrxiv": fetch_medrxiv(medrxiv_cfg.get("subjects", []), window),
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    all_articles: list[Article] = []
    for name, res in zip(tasks.keys(), results):
        if isinstance(res, Exception):
            log.error("Source %s : exception %s", name, res)
        else:
            log.info("Source %s : %d articles", name, len(res))
            all_articles.extend(res)
    return all_articles


def _assign_stars_fallback(articles: list[Article]) -> None:
    """Assigne des etoiles si Claude ne l'a pas fait (defensive)."""
    for a in articles:
        if a.relevance_score < 1:
            a.relevance_score = 1


async def run_pipeline(
    dry_run: bool,
    demo: bool,
    log: logging.Logger,
) -> int:
    """Pipeline complet. Retourne le code de sortie."""
    t0 = time.monotonic()
    today = date.today()

    if demo:
        from .demo_data import build_demo_articles
        log.info("=== MODE DEMO : articles synthetiques ===")
        articles = build_demo_articles()
        stats: dict = {
            "n_scraped": len(articles) * 3,
            "n_retained": len(articles),
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "window_hours": 36,
            "token_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            },
            "arxiv_categories": "physics.med-ph, q-bio.QM, cs.CV",
        }
    else:
        sources_cfg = load_sources()
        queries_cfg = load_queries()

        # 1. Fetch
        raw = await fetch_all_sources(sources_cfg, log)
        n_scraped = len(raw)

        # 2. Dedup intra-run
        unique = deduplicate(raw)

        # 3. Historique inter-runs
        history = load_history(HISTORY_PATH)
        fresh = filter_already_seen(unique, history)

        # 4. Scoring par mots-cles
        score_relevance(
            fresh,
            queries_cfg["keywords_strong"],
            queries_cfg["keywords_context"],
        )
        kept, ambiguous = filter_by_threshold(
            fresh, threshold=queries_cfg.get("threshold", 2)
        )
        # Les ambigus passent aussi a Claude (il trancheara sur 'relevant')
        candidates = kept + ambiguous
        log.info("Candidats Claude : %d (%d retenus + %d ambigus)",
                 len(candidates), len(kept), len(ambiguous))

        # 5. Claude : classifier + traduire + resumer + scorer
        valid_cat_ids = set(categories_map().keys())
        articles, token_usage = await enrich_with_claude(candidates, valid_cat_ids)

        # 6. Assignation etoile defensive
        _assign_stars_fallback(articles)

        # 7. Persistance historique
        save_history(HISTORY_PATH, history)

        stats = {
            "n_scraped": n_scraped,
            "n_retained": len(articles),
            "run_timestamp": datetime.now(timezone.utc).isoformat(),
            "window_hours": sources_cfg.get("window_hours", 36),
            "token_usage": token_usage,
            "arxiv_categories": ", ".join(
                sources_cfg.get("arxiv", {}).get("categories", [])
            ),
        }

    # 8. Render HTML
    output_path = OUTPUT_DIR / f"review_{today.isoformat()}.html"
    _, meta = render_review(articles, stats, output_path)

    # Aussi index.html (derniere revue, pour GitHub Pages)
    index_path = OUTPUT_DIR / "index.html"
    index_path.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")

    stats["duration_s"] = round(time.monotonic() - t0, 1)

    # Metadata JSON pour indexation / debug
    meta_json = OUTPUT_DIR / f"review_{today.isoformat()}.meta.json"
    meta_json.write_text(
        json.dumps(
            {
                "date": today.isoformat(),
                "n_articles": meta["n_articles"],
                "n_scraped": stats.get("n_scraped"),
                "counts": meta["counts"],
                "token_usage": stats.get("token_usage"),
                "duration_s": stats["duration_s"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # 9. Summary GitHub Actions
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        _write_gh_summary(summary_path, meta, stats)

    # 10. Email
    if dry_run or demo:
        log.info("Mode %s : email non envoye", "demo" if demo else "dry-run")
    else:
        try:
            archive_url = os.environ.get("PUBLIC_ARCHIVE_URL")
            send_email(meta, output_path, archive_url)
        except Exception as e:
            log.error("Envoi email echoue : %s", e, exc_info=True)
            return 2

    log.info("=== Termine en %ss : %d articles, %d rubriques ===",
             stats["duration_s"], meta["n_articles"], meta["n_categories"])
    return 0


def _write_gh_summary(
    path: str, meta: dict, stats: dict
) -> None:
    """Ecrit un resume pour le GitHub Actions summary panel."""
    lines = [
        f"# 🔬 Revue MN du {meta['date_fr']}",
        "",
        f"- **{meta['n_articles']} articles** retenus",
        f"- **{meta['n_categories']} rubriques** actives",
        f"- **{stats.get('n_scraped', '?')} articles** scrapés au total",
        f"- **Durée** : {stats.get('duration_s', '?')}s",
        f"- **Version** : v{__version__}",
        "",
        "## Répartition par rubrique",
        "",
        "| Rubrique | Articles |",
        "|---|---:|",
    ]
    for cat in meta["active_categories"]:
        lines.append(f"| {cat['emoji']} {cat['label']} | {meta['counts'][cat['id']]} |")

    tu = stats.get("token_usage", {})
    if tu:
        lines += [
            "",
            "## Tokens Claude",
            "",
            f"- Input : {tu.get('input_tokens', 0):,}",
            f"- Output : {tu.get('output_tokens', 0):,}",
            f"- Cache read : {tu.get('cache_read_input_tokens', 0):,}",
            f"- Cache write : {tu.get('cache_creation_input_tokens', 0):,}",
        ]

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    """Point d'entree CLI."""
    parser = argparse.ArgumentParser(
        description="Revue quotidienne de litterature en medecine nucleaire"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="N'envoie pas l'email, genere juste le HTML")
    parser.add_argument("--demo", action="store_true",
                        help="Genere un HTML avec des donnees synthetiques (offline)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Active les logs DEBUG")
    args = parser.parse_args()

    load_dotenv()
    log = setup_logging(verbose=args.verbose)
    log.info("=== nuclear-med-review v%s : demarrage ===", __version__)

    try:
        return asyncio.run(
            run_pipeline(dry_run=args.dry_run, demo=args.demo, log=log)
        )
    except KeyboardInterrupt:
        log.warning("Interruption utilisateur")
        return 130
    except Exception as e:
        log.error("Erreur fatale : %s", e, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
