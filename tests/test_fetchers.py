"""Tests unitaires des parseurs (offline, avec fixtures mockees)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.fetchers.pubmed import _build_query, _parse_xml
from src.fetchers.rss import _coerce_date, _extract_doi
from src.fetchers.arxiv import _matches_filter


PUBMED_XML_FIXTURE = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID Version="1">40012345</PMID>
      <Article>
        <Journal>
          <ISOAbbreviation>J Nucl Med</ISOAbbreviation>
          <JournalIssue>
            <PubDate><Year>2026</Year><Month>Apr</Month><Day>15</Day></PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Test [177Lu]Lu-PSMA-617 Dosimetry Study</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Prostate cancer therapy.</AbstractText>
          <AbstractText Label="METHODS">25 patients imaged.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Schmidt</LastName>
            <Initials>K</Initials>
            <AffiliationInfo><Affiliation>Hospital Zurich</Affiliation></AffiliationInfo>
          </Author>
          <Author><LastName>Weber</LastName><Initials>J</Initials></Author>
        </AuthorList>
      </Article>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">40012345</ArticleId>
        <ArticleId IdType="doi">10.2967/jnumed.2026.264000</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


def test_pubmed_build_query_includes_journals_and_date():
    q = _build_query(["J Nucl Med", "Radiology"], window_hours=36)
    assert '"J Nucl Med"[Journal]' in q
    assert '"Radiology"[Journal]' in q
    assert "[EDAT]" in q


def test_pubmed_parse_xml_extracts_core_fields():
    articles = _parse_xml(PUBMED_XML_FIXTURE)
    assert len(articles) == 1
    a = articles[0]
    assert a.pmid == "40012345"
    assert a.doi == "10.2967/jnumed.2026.264000"
    assert "PSMA" in a.title
    assert "BACKGROUND" in a.abstract
    assert "METHODS" in a.abstract
    assert a.journal == "J Nucl Med"
    assert a.authors == ["Schmidt K", "Weber J"]
    assert a.first_affiliation == "Hospital Zurich"
    assert a.published_at is not None
    assert a.published_at.year == 2026
    assert a.published_at.month == 4


def test_pubmed_parse_xml_handles_empty():
    assert _parse_xml("") == []
    assert _parse_xml("<PubmedArticleSet/>") == []


def test_rss_coerce_date_rfc822():
    e = {"published": "Mon, 21 Apr 2026 10:00:00 +0000"}
    d = _coerce_date(e)
    assert d is not None
    assert d.year == 2026 and d.month == 4 and d.day == 21


def test_rss_coerce_date_missing_returns_none():
    assert _coerce_date({}) is None
    assert _coerce_date({"published": "not a date"}) is None


def test_rss_extract_doi_from_link():
    e = {"link": "https://doi.org/10.2967/jnumed.2026.264000"}
    assert _extract_doi(e) == "10.2967/jnumed.2026.264000"


def test_rss_extract_doi_missing():
    assert _extract_doi({"link": "https://example.com/article"}) is None


def test_arxiv_relevance_filter():
    text = "A new total-body PET reconstruction method"
    assert _matches_filter(text, ["PET", "SPECT"]) is True
    assert _matches_filter(text, ["MRI", "SPECT"]) is False
    # Case insensitive
    assert _matches_filter("PET/CT study", ["pet"]) is True


if __name__ == "__main__":
    # Permet d'executer directement le fichier
    import traceback
    tests = [
        test_pubmed_build_query_includes_journals_and_date,
        test_pubmed_parse_xml_extracts_core_fields,
        test_pubmed_parse_xml_handles_empty,
        test_rss_coerce_date_rfc822,
        test_rss_coerce_date_missing_returns_none,
        test_rss_extract_doi_from_link,
        test_rss_extract_doi_missing,
        test_arxiv_relevance_filter,
    ]
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
