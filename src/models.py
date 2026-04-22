"""Modeles de donnees partages dans le pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Article:
    """Represente un article scientifique recupere d'une source."""

    # Identifiants
    source: str                      # "pubmed" | "rss" | "arxiv" | "medrxiv"
    source_name: str = ""            # Nom detaille (ex: "JNM RSS", "PubMed")
    doi: str | None = None
    pmid: str | None = None
    arxiv_id: str | None = None
    url: str | None = None

    # Metadonnees bibliographiques
    title: str = ""
    title_fr: str | None = None      # Traduction FR (remplie par summarizer)
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    first_affiliation: str | None = None
    journal: str = ""
    published_at: datetime | None = None

    # Scoring et classification (remplis par processors)
    keyword_score: float = 0.0
    relevance_score: int = 0          # 1 / 2 / 3 etoiles
    category_id: str | None = None    # ID de rubrique
    tags: list[str] = field(default_factory=list)

    # Resume FR structure (rempli par summarizer)
    summary_fr: dict[str, str] = field(default_factory=dict)
    # Cles attendues : context, method, results, implication

    def unique_key(self) -> str:
        """Cle de deduplication stricte."""
        if self.doi:
            return f"doi:{self.doi.lower().strip()}"
        if self.pmid:
            return f"pmid:{self.pmid}"
        if self.arxiv_id:
            return f"arxiv:{self.arxiv_id}"
        return f"title:{self.title.lower().strip()}"

    def to_dict(self) -> dict[str, Any]:
        """Serialisation pour Jinja et logs."""
        return {
            "source": self.source,
            "source_name": self.source_name,
            "doi": self.doi,
            "pmid": self.pmid,
            "arxiv_id": self.arxiv_id,
            "url": self.url,
            "title": self.title,
            "title_fr": self.title_fr,
            "abstract": self.abstract,
            "authors": self.authors,
            "first_affiliation": self.first_affiliation,
            "journal": self.journal,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
            "keyword_score": self.keyword_score,
            "relevance_score": self.relevance_score,
            "category_id": self.category_id,
            "tags": self.tags,
            "summary_fr": self.summary_fr,
        }
