from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "ai": ["ai", "artificial intelligence", "人工智能"],
    "data_mining": ["data mining", "挖掘", "数据挖掘", "数据库", "data engineering"],
    "machine_learning": ["machine learning", "ml", "机器学习"],
    "software_engineering": ["software engineering", "se", "软件工程"],
}


@dataclass
class QueryIntent:
    domain: str | None
    year: int | None
    venue: str | None


def parse_query(query: str, cfg_domains: dict[str, Any], venue_aliases: dict[str, list[str]]) -> QueryIntent:
    q = (query or "").strip().lower()
    if not q:
        return QueryIntent(domain=None, year=None, venue=None)

    year: int | None = None
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match:
        y = int(year_match.group(1))
        if 2000 <= y <= 2100:
            year = y

    domain: str | None = None
    for key, kws in DOMAIN_KEYWORDS.items():
        if any(kw in q for kw in kws):
            domain = key
            break

    venue: str | None = None
    # Try exact venue keys first
    all_venues: list[str] = []
    for dcfg in cfg_domains.values():
        for v in dcfg.get("venues", []):
            if isinstance(v, str):
                all_venues.append(v)

    for v in all_venues:
        if v.lower() in q:
            venue = v
            break

    # Then try aliases
    if not venue:
        for canonical, aliases in venue_aliases.items():
            candidates = [canonical] + (aliases or [])
            if any(str(c).lower() in q for c in candidates if isinstance(c, str)):
                # Canonical may be lowercase key; map to configured venue spelling when possible.
                for v in all_venues:
                    if v.lower() == canonical.lower():
                        venue = v
                        break
                if not venue:
                    venue = canonical
                break

    return QueryIntent(domain=domain, year=year, venue=venue)
