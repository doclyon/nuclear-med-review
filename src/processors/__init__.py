"""Modules de traitement : dedup, classification, resume."""

from .deduplicate import deduplicate, load_history, save_history, filter_already_seen
from .classifier import score_relevance, filter_by_threshold
from .summarizer import enrich_with_claude

__all__ = [
    "deduplicate",
    "load_history",
    "save_history",
    "filter_already_seen",
    "score_relevance",
    "filter_by_threshold",
    "enrich_with_claude",
]
