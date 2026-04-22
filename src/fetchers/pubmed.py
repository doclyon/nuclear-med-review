"""Fetcher PubMed via l'API NCBI E-utilities (esearch + efetch)."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import httpx

from ..models import Article

log = logging.getLogger("revue.pubmed")

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
ESEARCH = f"{EUTILS}/esearch.fcgi"
EFETCH = f"{EUTILS}/efetch.fcgi"

# NCBI : 3 req/s sans cle, 10 avec cle. On reste prudent.
_RATE = asyncio.Semaphore(3)


def _build_query(journals: list[str], window_hours: int) -> str:
    """Construit la requete PubMed avec filtre journal + date."""
    journal_expr = " OR ".join(f'"{j}"[Journal]' for j in journals)
    # Fenetre glissante : on utilise le champ EDAT (Entrez date) plus recent
    # que DP (publication date) pour attraper les articles indexes recents.
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    # Filtre EDAT : "YYYY/MM/DD"[EDAT] : "3000"[EDAT]
    edat = since.strftime("%Y/%m/%d")
    date_expr = f'("{edat}"[EDAT] : "3000"[EDAT])'
    return f"({journal_expr}) AND {date_expr}"


async def _esearch(
    client: httpx.AsyncClient, query: str, api_key: str | None, retmax: int
) -> list[str]:
    """Recupere la liste de PMID correspondant a la requete."""
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": retmax,
        "sort": "date",
    }
    if api_key:
        params["api_key"] = api_key
    async with _RATE:
        r = await client.get(ESEARCH, params=params, timeout=30.0)
    r.raise_for_status()
    data = r.json()
    ids = data.get("esearchresult", {}).get("idlist", [])
    log.info("PubMed esearch : %d PMID pour %d caracteres de requete", len(ids), len(query))
    return ids


async def _efetch(
    client: httpx.AsyncClient, pmids: list[str], api_key: str | None
) -> str:
    """Recupere le XML complet (titres, auteurs, abstracts)."""
    if not pmids:
        return ""
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    }
    if api_key:
        params["api_key"] = api_key
    async with _RATE:
        r = await client.get(EFETCH, params=params, timeout=60.0)
    r.raise_for_status()
    return r.text


def _parse_date(elem: ET.Element | None) -> datetime | None:
    """Extrait une date depuis un element PubDate/DateCompleted."""
    if elem is None:
        return None
    year = elem.findtext("Year")
    month = elem.findtext("Month") or "1"
    day = elem.findtext("Day") or "1"
    if not year:
        return None
    # Conversion des mois en texte si besoin
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }
    try:
        m = int(month) if month.isdigit() else months.get(month[:3], 1)
        return datetime(int(year), m, int(day), tzinfo=timezone.utc)
    except (ValueError, KeyError):
        return None


def _parse_xml(xml_text: str) -> list[Article]:
    """Parse la reponse XML d'efetch et retourne une liste d'Article."""
    if not xml_text.strip():
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.error("Echec parsing XML PubMed : %s", e)
        return []

    articles: list[Article] = []
    for pa in root.findall(".//PubmedArticle"):
        medline = pa.find("MedlineCitation")
        if medline is None:
            continue
        pmid = medline.findtext("PMID") or ""
        art = medline.find("Article")
        if art is None:
            continue

        title = (art.findtext("ArticleTitle") or "").strip()

        # Abstract : peut contenir plusieurs AbstractText
        abstract_parts: list[str] = []
        for at in art.findall(".//Abstract/AbstractText"):
            label = at.get("Label")
            text = "".join(at.itertext()).strip()
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = " ".join(abstract_parts)

        # Journal
        journal = art.findtext(".//Journal/ISOAbbreviation") or art.findtext(
            ".//Journal/Title"
        ) or ""

        # Date de publication
        pub_date = _parse_date(art.find(".//Journal/JournalIssue/PubDate"))
        if pub_date is None:
            pub_date = _parse_date(medline.find(".//DateCompleted"))

        # Auteurs
        authors: list[str] = []
        first_aff: str | None = None
        for i, au in enumerate(art.findall(".//AuthorList/Author")):
            last = au.findtext("LastName") or ""
            init = au.findtext("Initials") or ""
            name = f"{last} {init}".strip()
            if name:
                authors.append(name)
            if i == 0:
                aff = au.findtext(".//Affiliation")
                if aff:
                    first_aff = aff.strip()

        # DOI
        doi: str | None = None
        for aid in pa.findall(".//ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = (aid.text or "").strip() or None
                break

        url = f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

        articles.append(
            Article(
                source="pubmed",
                source_name="PubMed",
                doi=doi,
                pmid=pmid,
                url=url,
                title=title,
                abstract=abstract,
                authors=authors,
                first_affiliation=first_aff,
                journal=journal,
                published_at=pub_date,
            )
        )
    return articles


async def fetch_pubmed(
    journals: list[str],
    window_hours: int = 36,
    max_results: int = 200,
) -> list[Article]:
    """Interroge PubMed pour les journaux donnes sur la fenetre glissante."""
    api_key = os.environ.get("PUBMED_API_KEY")
    query = _build_query(journals, window_hours)
    async with httpx.AsyncClient() as client:
        try:
            pmids = await _esearch(client, query, api_key, max_results)
        except httpx.HTTPError as e:
            log.error("PubMed esearch echec : %s", e)
            return []
        if not pmids:
            return []
        # efetch en un seul appel (PubMed accepte 200+ PMIDs)
        try:
            xml_text = await _efetch(client, pmids, api_key)
        except httpx.HTTPError as e:
            log.error("PubMed efetch echec : %s", e)
            return []
    articles = _parse_xml(xml_text)
    log.info("PubMed : %d articles parses", len(articles))
    return articles
