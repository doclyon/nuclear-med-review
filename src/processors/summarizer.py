"""Enrichissement des articles via l'API Claude (tri ambigu, classification,
resume FR, score etoiles). Utilise le prompt caching pour reduire les couts."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import load_categories
from ..models import Article

log = logging.getLogger("revue.summarizer")

# Modele fixe : Sonnet 4.6, bon compromis qualite/cout pour du medical FR.
CLAUDE_MODEL = "claude-sonnet-4-6"

# Concurrence des appels (6 en parallele = confortable pour le Tier 1).
CONCURRENCY = 6

# Token counters (cumul pour le log final)
_token_stats: dict[str, int] = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read_input_tokens": 0,
    "cache_creation_input_tokens": 0,
}


def _category_block() -> str:
    """Bloc texte decrivant les 10 rubriques, mis en cache par Claude."""
    cats = load_categories()
    lines = []
    for c in cats:
        lines.append(f"- {c['id']} ({c['emoji']} {c['label']}) : {c['description'].strip()}")
    return "\n".join(lines)


SYSTEM_PROMPT = """Tu es un assistant medical specialise en medecine nucleaire \
qui aide un praticien a effectuer sa veille bibliographique quotidienne.

Ton role pour chaque article soumis :
1. Juger si l'article est **pertinent** pour un medecin nucleaire francophone
2. Attribuer une **categorie** unique parmi la liste fournie
3. Attribuer jusqu'a **5 tags** courts (pathologie, traceur, technique)
4. Produire un **resume FR structure** en 4 blocs courts (1-2 lignes chacun) :
   - context : pourquoi cette etude
   - method : design, population, technique
   - results : chiffres cles
   - implication : ce que ca change pour la pratique
5. Attribuer un **score d'etoiles** de 1 a 3 :
   - 3 : article majeur (essai pivot, guideline, technique de rupture)
   - 2 : article interessant, lecture conseillee
   - 1 : article mineur ou tres niche
6. Traduire le **titre** en francais, concis et fidele.

Categories disponibles (id : description) :
{category_block}

Reponds STRICTEMENT en JSON valide, avec ce schema :
{{
  "relevant": true | false,
  "title_fr": "string",
  "category_id": "string (un id de la liste)",
  "tags": ["string", ...],
  "stars": 1 | 2 | 3,
  "summary_fr": {{
    "context": "string",
    "method": "string",
    "results": "string",
    "implication": "string"
  }},
  "rejection_reason": "string (seulement si relevant=false, sinon null)"
}}

Si l'article est hors-sujet medecine nucleaire/imagerie, mets relevant=false \
et laisse les autres champs null (sauf rejection_reason).
Sois concis, medical, sans remplissage. Pas de phrases comme "cette etude \
montre que" : va directement a l'information. Chiffres et unites toujours."""


def _build_system() -> list[dict[str, Any]]:
    """System prompt avec cache_control pour bénéficier du prompt caching."""
    content = SYSTEM_PROMPT.format(category_block=_category_block())
    return [
        {
            "type": "text",
            "text": content,
            "cache_control": {"type": "ephemeral"},
        }
    ]


def _build_user(article: Article) -> str:
    """Message utilisateur pour un article donne."""
    authors = ", ".join(article.authors[:6])
    if len(article.authors) > 6:
        authors += " et al."
    return (
        f"Source : {article.source_name} ({article.journal})\n"
        f"Titre : {article.title}\n"
        f"Auteurs : {authors}\n"
        f"Affiliation 1er auteur : {article.first_affiliation or 'non precisee'}\n"
        f"DOI : {article.doi or 'N/A'}\n\n"
        f"Abstract :\n{article.abstract or '[abstract non disponible]'}"
    )


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extrait le premier objet JSON trouve dans la reponse."""
    # Cas le plus courant : reponse = JSON pur
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Sinon, chercher un bloc ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Dernier recours : trouver la premiere accolade equilibree
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
async def _ask_claude(
    client: AsyncAnthropic, article: Article
) -> dict[str, Any] | None:
    """Envoie un article a Claude, retourne le dict analyse."""
    msg = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=_build_system(),
        messages=[{"role": "user", "content": _build_user(article)}],
    )
    # Cumul des tokens
    u = msg.usage
    _token_stats["input_tokens"] += getattr(u, "input_tokens", 0) or 0
    _token_stats["output_tokens"] += getattr(u, "output_tokens", 0) or 0
    _token_stats["cache_read_input_tokens"] += (
        getattr(u, "cache_read_input_tokens", 0) or 0
    )
    _token_stats["cache_creation_input_tokens"] += (
        getattr(u, "cache_creation_input_tokens", 0) or 0
    )

    # Texte de la reponse
    parts = []
    for block in msg.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return _extract_json("\n".join(parts))


async def _process_one(
    client: AsyncAnthropic,
    article: Article,
    sem: asyncio.Semaphore,
) -> Article | None:
    """Traite un article : renvoie Article enrichi ou None si rejete."""
    async with sem:
        try:
            data = await _ask_claude(client, article)
        except Exception as e:
            log.warning("Claude echec sur '%s' : %s", article.title[:80], e)
            return None

    if not data:
        log.warning("Claude : JSON illisible pour '%s'", article.title[:80])
        return None

    if not data.get("relevant"):
        log.debug("Rejete par Claude : %s (%s)",
                  article.title[:80], data.get("rejection_reason"))
        return None

    # Validation et assignation
    article.title_fr = (data.get("title_fr") or "").strip() or None
    article.category_id = data.get("category_id")
    article.tags = [t for t in (data.get("tags") or []) if isinstance(t, str)][:5]
    stars = data.get("stars", 1)
    article.relevance_score = max(1, min(3, int(stars))) if isinstance(stars, int) else 1
    article.summary_fr = data.get("summary_fr") or {}
    return article


async def enrich_with_claude(
    articles: list[Article],
    valid_category_ids: set[str],
) -> tuple[list[Article], dict[str, int]]:
    """Classe/resume/score tous les articles via Claude, en parallele.

    Retourne (articles enrichis & retenus, stats de tokens).
    """
    if not articles:
        return [], dict(_token_stats)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY absent de l'environnement")

    client = AsyncAnthropic(api_key=api_key)
    sem = asyncio.Semaphore(CONCURRENCY)

    log.info("Claude : traitement de %d articles (concurrence=%d)",
             len(articles), CONCURRENCY)
    results = await asyncio.gather(
        *[_process_one(client, a, sem) for a in articles],
        return_exceptions=False,
    )

    enriched: list[Article] = []
    for r in results:
        if r is None:
            continue
        if r.category_id not in valid_category_ids:
            log.warning("Categorie invalide '%s' pour '%s', fallback general_medicine",
                        r.category_id, r.title[:60])
            r.category_id = "general_medicine"
        enriched.append(r)

    log.info(
        "Claude : %d -> %d retenus | tokens in=%d out=%d cache_read=%d cache_write=%d",
        len(articles),
        len(enriched),
        _token_stats["input_tokens"],
        _token_stats["output_tokens"],
        _token_stats["cache_read_input_tokens"],
        _token_stats["cache_creation_input_tokens"],
    )
    return enriched, dict(_token_stats)
