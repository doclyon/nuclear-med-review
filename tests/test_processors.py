"""Tests unitaires des processors (dedup, scoring)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import Article
from src.processors.classifier import filter_by_threshold, score_relevance
from src.processors.deduplicate import (
    _normalize_title,
    deduplicate,
    filter_already_seen,
)


def _make(title: str, doi: str | None = None, pmid: str | None = None,
          abstract: str = "", source: str = "pubmed") -> Article:
    return Article(
        source=source,
        source_name="test",
        doi=doi,
        pmid=pmid,
        title=title,
        abstract=abstract,
        journal="Test",
        published_at=datetime.now(timezone.utc),
    )


def test_normalize_title_removes_punct_and_case():
    assert _normalize_title("Hello, World!") == "hello world"
    assert _normalize_title("[68Ga]Ga-DOTATATE PET/CT") == "68ga ga dotatate pet ct"


def test_dedup_by_doi_strict():
    a1 = _make("Study A v1", doi="10.1/abc", abstract="short")
    a2 = _make("Study A v2", doi="10.1/abc", abstract="much longer abstract here")
    out = deduplicate([a1, a2])
    assert len(out) == 1
    # Doit garder l'abstract le plus long
    assert out[0].abstract == "much longer abstract here"


def test_dedup_by_pmid_strict():
    a1 = _make("Title", pmid="12345")
    a2 = _make("Title variant", pmid="12345")
    assert len(deduplicate([a1, a2])) == 1


def test_dedup_fuzzy_title():
    a1 = _make("Total-Body PET/CT for Whole-Body Dosimetry of Lu-177-PSMA-617",
               doi="10.1/a")
    a2 = _make("Total-Body PET/CT for Whole-Body Dosimetry of Lu-177-PSMA-617.",
               doi="10.1/b")
    out = deduplicate([a1, a2])
    assert len(out) == 1


def test_dedup_keeps_distinct_articles():
    a1 = _make("Study A", doi="10.1/a")
    a2 = _make("Completely Different Topic About Cardiac Imaging", doi="10.1/b")
    assert len(deduplicate([a1, a2])) == 2


def test_score_relevance_strong_and_context():
    strong = ["PSMA", "Lu-177"]
    context = ["molecular imaging"]
    arts = [
        _make("PSMA PET study", abstract="Lu-177 therapy with molecular imaging"),
        _make("Unrelated cardiology", abstract="ECG monitoring"),
    ]
    score_relevance(arts, strong, context)
    assert arts[0].keyword_score == 2 + 2 + 1  # PSMA + Lu-177 + molecular imaging
    assert arts[1].keyword_score == 0


def test_filter_by_threshold_three_buckets():
    a = _make("x"); a.keyword_score = 3
    b = _make("y"); b.keyword_score = 1.5
    c = _make("z"); c.keyword_score = 0
    kept, amb = filter_by_threshold([a, b, c], threshold=2)
    assert a in kept and b in amb and c not in kept and c not in amb


def test_filter_already_seen_excludes_known():
    a = _make("A", doi="10.1/a")
    b = _make("B", doi="10.1/b")
    history = {"doi:10.1/a": "2026-04-22"}
    fresh = filter_already_seen([a, b], history)
    assert len(fresh) == 1 and fresh[0].doi == "10.1/b"
    assert "doi:10.1/b" in history  # b ajoute


def test_renderer_basic():
    """Verifie que le renderer produit du HTML non vide."""
    from src.renderer import render_review
    import tempfile
    a = _make("Test", doi="10.1/x", abstract="abc")
    a.category_id = "theranostics"
    a.relevance_score = 2
    a.summary_fr = {"context": "c", "method": "m", "results": "r", "implication": "i"}
    a.title_fr = "Titre test"
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "out.html"
        html, meta = render_review([a], {"n_scraped": 10}, out)
        assert "Test" in html
        assert "Titre test" in html
        assert "theranostics" in html or "Théranostique" in html
        assert meta["n_articles"] == 1


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"OK  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__} : {e}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} tests passent")
    sys.exit(1 if failed else 0)
