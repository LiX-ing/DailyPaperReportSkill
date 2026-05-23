from __future__ import annotations

from datetime import date

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .openalex_client import Paper

SEMANTIC_SCHOLAR_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def _build_session() -> requests.Session:
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def fetch_candidates_semantic_scholar(
    year_window: int,
    max_candidates: int,
    venues: list[str],
    query_text: str = "",
    api_key: str | None = None,
    verify_ssl: bool = True,
) -> list[Paper]:
    current_year = date.today().year
    from_year = current_year - year_window + 1

    session = _build_session()
    headers: dict[str, str] = {}
    if api_key:
        headers["x-api-key"] = api_key

    results: list[Paper] = []
    seen: set[str] = set()

    # Use one aggregated query to reduce rate-limit risk on public (no-key) access.
    query_terms = [v for v in venues[:6] if v]
    if query_text.strip():
        query_terms.insert(0, query_text.strip())
    if not query_terms:
        query_terms = ["artificial intelligence", "machine learning"]
    query = " OR ".join(query_terms)

    for offset in (0, 100):
        params = {
            "query": query,
            "limit": "100",
            "offset": str(offset),
            "fields": "paperId,title,abstract,year,venue,journal,url,externalIds",
        }
        resp = session.get(
            SEMANTIC_SCHOLAR_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=30,
            verify=verify_ssl,
        )
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("data", []):
            year = item.get("year") or 0
            if not isinstance(year, int) or year < from_year or year > current_year:
                continue

            paper_id = item.get("paperId", "")
            if not paper_id or paper_id in seen:
                continue
            seen.add(paper_id)

            journal = item.get("journal") or {}
            venue_name = item.get("venue") or journal.get("name", "")
            external_ids = item.get("externalIds") or {}
            doi = external_ids.get("DOI", "")

            paper = Paper(
                paper_id=paper_id,
                title=item.get("title", ""),
                abstract=(item.get("abstract") or "").strip(),
                year=year,
                venue=venue_name,
                venue_candidates=[v for v in [venue_name, venue] if v],
                doi=doi,
                url=item.get("url", ""),
            )
            if paper.title:
                results.append(paper)

            if len(results) >= max_candidates * 2:
                return results

        # Stop early when API returns fewer than asked rows.
        if len(data.get("data", [])) < 100:
            break

    return results
