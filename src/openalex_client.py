from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
OPENALEX_SOURCES_URL = "https://api.openalex.org/sources"
COMPUTER_SCIENCE_CONCEPT_ID = "C41008148"
DEFAULT_FALLBACK_ALIASES: dict[str, list[str]] = {
    # Minimal safety net when config is incomplete.
    "neurips": ["neural information processing systems"],
    "icml": ["international conference on machine learning"],
    "iclr": ["international conference on learning representations"],
    "cvpr": ["computer vision and pattern recognition"],
    "icse": ["international conference on software engineering"],
}


@dataclass
class Paper:
    paper_id: str
    title: str
    abstract: str
    year: int
    venue: str
    venue_candidates: list[str]
    doi: str
    url: str


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _extract_source_names(item: dict[str, Any]) -> list[str]:
    names: list[str] = []
    primary_location = _as_dict(item.get("primary_location"))
    primary_source = _as_dict(primary_location.get("source"))
    display_name = primary_source.get("display_name")
    if isinstance(display_name, str) and display_name.strip():
        names.append(display_name.strip())

    for loc in _as_list(item.get("locations")):
        loc_obj = _as_dict(loc)
        source_obj = _as_dict(loc_obj.get("source"))
        name = source_obj.get("display_name")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())

    # de-dup keep order
    return list(dict.fromkeys(names))


def _decode_inverted_abstract(inv: dict[str, list[int]] | None) -> str:
    if not inv:
        return ""

    max_index = max((max(pos) for pos in inv.values() if pos), default=-1)
    if max_index < 0:
        return ""

    words = [""] * (max_index + 1)
    for token, positions in inv.items():
        for p in positions:
            if 0 <= p < len(words):
                words[p] = token
    return " ".join(w for w in words if w).strip()


def fetch_candidates(
    year_window: int,
    max_candidates: int,
    venues: list[str] | None = None,
    venue_aliases: dict[str, list[str]] | None = None,
    email: str | None = None,
    api_key: str | None = None,
    verify_ssl: bool = True,
) -> list[Paper]:
    current_year = date.today().year
    from_year = current_year - year_window + 1

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

    aliases = venue_aliases or {}
    seeds: list[str] = []
    for v in venues or []:
        seeds.append(v)
        key = v.lower()
        seeds.extend(aliases.get(v, []))
        seeds.extend(aliases.get(key, []))
        seeds.extend(DEFAULT_FALLBACK_ALIASES.get(key, []))
    venue_terms = [s.strip() for s in seeds if isinstance(s, str) and s.strip()]
    venue_terms = list(dict.fromkeys(venue_terms))
    if not venue_terms:
        venue_terms = ["machine learning", "artificial intelligence"]

    def _common_params() -> dict[str, str]:
        p: dict[str, str] = {}
        if api_key:
            p["api_key"] = api_key
        if email:
            p["mailto"] = email
        return p

    def _resolve_source_ids(terms: list[str]) -> list[str]:
        source_ids: list[str] = []
        for term in terms:
            params = {"search": term, "per-page": "5"}
            params.update(_common_params())
            resp = session.get(
                OPENALEX_SOURCES_URL,
                params=params,
                timeout=30,
                verify=verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            for src in data.get("results", []):
                src_id = src.get("id")
                if isinstance(src_id, str) and src_id:
                    source_ids.append(src_id)
        return list(dict.fromkeys(source_ids))

    source_ids = _resolve_source_ids(venue_terms[:20])

    results: list[Paper] = []
    seen_ids: set[str] = set()
    per_page = 100

    # Query works by resolved source ids (strict venue targeting).
    if source_ids:
        batch_size = 20
        for i in range(0, len(source_ids), batch_size):
            batch = source_ids[i : i + batch_size]
            source_filter = "|".join(batch)
            params = {
                "filter": (
                    f"publication_year:{from_year}|{current_year},"
                    f"has_abstract:true,type:article|proceedings-article,"
                    f"primary_location.source.id:{source_filter}"
                ),
                "sort": "publication_date:desc",
                "per-page": str(per_page),
                "page": "1",
            }
            params.update(_common_params())

            resp = session.get(
                OPENALEX_WORKS_URL, params=params, timeout=30, verify=verify_ssl
            )
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("results", []):
                primary_location = _as_dict(item.get("primary_location"))
                source_names = _extract_source_names(item)
                source = source_names[0] if source_names else ""
                paper_id = item.get("id", "")
                if not paper_id or paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)

                doi = item.get("doi", "")
                paper = Paper(
                    paper_id=paper_id,
                    title=item.get("display_name", ""),
                    abstract=_decode_inverted_abstract(item.get("abstract_inverted_index")),
                    year=item.get("publication_year") or 0,
                    venue=source,
                    venue_candidates=source_names,
                    doi=doi,
                    url=primary_location.get("landing_page_url", ""),
                )
                if paper.title:
                    results.append(paper)

            if len(results) >= max_candidates * 3:
                break
    else:
        # Last fallback: broad CS query.
        params = {
            "filter": (
                f"publication_year:{from_year}|{current_year},"
                f"has_abstract:true,concepts.id:{COMPUTER_SCIENCE_CONCEPT_ID},"
                "type:article|proceedings-article"
            ),
            "sort": "publication_date:desc",
            "per-page": str(per_page),
            "page": "1",
        }
        params.update(_common_params())
        resp = session.get(OPENALEX_WORKS_URL, params=params, timeout=30, verify=verify_ssl)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("results", []):
            primary_location = _as_dict(item.get("primary_location"))
            source_names = _extract_source_names(item)
            source = source_names[0] if source_names else ""
            paper_id = item.get("id", "")
            if not paper_id or paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)
            paper = Paper(
                paper_id=paper_id,
                title=item.get("display_name", ""),
                abstract=_decode_inverted_abstract(item.get("abstract_inverted_index")),
                year=item.get("publication_year") or 0,
                venue=source,
                venue_candidates=source_names,
                doi=item.get("doi", ""),
                url=primary_location.get("landing_page_url", ""),
            )
            if paper.title:
                results.append(paper)

    return results


def match_by_venues(
    papers: list[Paper],
    venues: list[str],
    venue_aliases: dict[str, list[str]] | None = None,
) -> list[Paper]:
    aliases = venue_aliases or {}
    venue_keys: list[str] = []
    for venue in venues:
        key = venue.lower()
        venue_keys.append(key)
        configured_aliases = aliases.get(venue, []) or aliases.get(key, [])
        venue_keys.extend(a.lower() for a in configured_aliases)
        # Last-resort fallback to keep basic usability if aliases are absent.
        venue_keys.extend(DEFAULT_FALLBACK_ALIASES.get(key, []))

    # Keep order while removing duplicates.
    unique_keys = list(dict.fromkeys(venue_keys))

    matched: list[Paper] = []
    for p in papers:
        candidates = [c.lower() for c in (p.venue_candidates or []) if c]
        if not candidates and p.venue:
            candidates = [p.venue.lower()]
        if any(any(key in name for key in unique_keys) for name in candidates):
            matched.append(p)
    return matched
