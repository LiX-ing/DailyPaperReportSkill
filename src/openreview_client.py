from __future__ import annotations

from datetime import date

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .openalex_client import Paper


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


def _content_value(content: dict, key: str) -> str:
    if not isinstance(content, dict):
        return ""
    val = content.get(key)
    if isinstance(val, dict):
        inner = val.get("value")
        return inner if isinstance(inner, str) else ""
    if isinstance(val, str):
        return val
    return ""


def _expand_venue_ids(templates: list[str], from_year: int, to_year: int) -> list[str]:
    out: list[str] = []
    for year in range(from_year, to_year + 1):
        for t in templates:
            out.append(t.replace("{year}", str(year)))
    # de-dup keep order
    return list(dict.fromkeys(out))


def fetch_candidates_openreview(
    year_window: int,
    max_candidates: int,
    venue_templates: list[str],
    base_url: str = "https://api2.openreview.net",
    verify_ssl: bool = True,
) -> list[Paper]:
    current_year = date.today().year
    from_year = current_year - year_window + 1

    venue_ids = _expand_venue_ids(venue_templates, from_year, current_year)
    if not venue_ids:
        return []

    session = _build_session()
    results: list[Paper] = []
    seen: set[str] = set()

    for venue_id in venue_ids:
        offset = 0
        limit = 100
        while True:
            params = {
                "venueid": venue_id,
                "limit": str(limit),
                "offset": str(offset),
                "source": "forum",
            }
            resp = session.get(
                f"{base_url.rstrip('/')}/notes/search",
                params=params,
                timeout=30,
                verify=verify_ssl,
            )
            resp.raise_for_status()
            data = resp.json()
            notes = data.get("notes", [])
            if not notes:
                break

            for note in notes:
                paper_id = note.get("id", "")
                if not paper_id or paper_id in seen:
                    continue
                seen.add(paper_id)

                content = note.get("content") or {}
                title = _content_value(content, "title")
                abstract = _content_value(content, "abstract")
                if not title:
                    continue

                paper = Paper(
                    paper_id=paper_id,
                    title=title,
                    abstract=abstract,
                    year=from_year,
                    venue=venue_id,
                    venue_candidates=[venue_id],
                    doi="",
                    url=f"https://openreview.net/forum?id={paper_id}",
                )
                results.append(paper)
                if len(results) >= max_candidates * 2:
                    return results

            if len(notes) < limit:
                break
            offset += limit

    return results
