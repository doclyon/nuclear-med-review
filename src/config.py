"""Chargement des fichiers de configuration YAML."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@lru_cache(maxsize=None)
def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_sources() -> dict[str, Any]:
    """Retourne la config des sources (sources.yaml)."""
    return _load_yaml("sources.yaml")


def load_queries() -> dict[str, Any]:
    """Retourne la config des mots-cles (queries.yaml)."""
    return _load_yaml("queries.yaml")


def load_categories() -> list[dict[str, Any]]:
    """Retourne la liste ordonnee des rubriques (categories.yaml)."""
    return _load_yaml("categories.yaml")["categories"]


def categories_map() -> dict[str, dict[str, Any]]:
    """Dictionnaire id -> categorie, pour acces rapide."""
    return {c["id"]: c for c in load_categories()}
