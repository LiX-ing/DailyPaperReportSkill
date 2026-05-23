from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from .query_parser import parse_query


NO_SAVE_PATTERNS = [
    "不需要落盘",
    "不要落盘",
    "不用落盘",
    "不保存",
    "仅回答",
    "临时看",
    "no save",
    "do not save",
    "dont save",
]

STOPWORDS = {
    "give",
    "me",
    "paper",
    "papers",
    "about",
    "with",
    "from",
    "for",
    "a",
    "an",
    "the",
    "of",
    "and",
    "or",
    "in",
    "on",
    "to",
    "顶会",
    "顶刊",
    "论文",
    "一篇",
    "给我",
    "给我一篇",
    "发表",
    "关于",
    "领域",
    "今年",
    "去年",
    "不保存",
    "不要落盘",
    "不需要落盘",
    "不用落盘",
}


@dataclass
class QueryPlan:
    raw_query: str
    domain: str
    venue: str | None
    year: int | None
    year_start: int | None
    year_end: int | None
    target_venues: list[str]
    keywords: list[str]
    should_persist: bool
    source_query_text: str

    @property
    def has_constraints(self) -> bool:
        return bool(self.raw_query.strip())


def _extract_year_range(q: str) -> tuple[int | None, int | None]:
    m = re.search(r"(20\d{2})\s*(?:-|~|到|to)\s*(20\d{2})", q, flags=re.IGNORECASE)
    if not m:
        return None, None
    y1 = int(m.group(1))
    y2 = int(m.group(2))
    lo, hi = min(y1, y2), max(y1, y2)
    current = date.today().year
    if lo < 2000:
        lo = 2000
    if hi > current:
        hi = current
    if lo > hi:
        return None, None
    return lo, hi


def _extract_keywords(q: str, removable_terms: list[str]) -> list[str]:
    cleaned = q.lower()
    for term in removable_terms:
        t = (term or "").strip().lower()
        if t:
            cleaned = cleaned.replace(t, " ")
    cleaned = re.sub(r"20\d{2}", " ", cleaned)
    cleaned = re.sub(r"([a-z0-9])([\u4e00-\u9fff])", r"\1 \2", cleaned)
    cleaned = re.sub(r"([\u4e00-\u9fff])([a-z0-9])", r"\1 \2", cleaned)
    tokens = re.findall(r"[a-z0-9\u4e00-\u9fff]{2,}", cleaned)
    out: list[str] = []
    for token in tokens:
        if token in STOPWORDS:
            continue
        if token.isdigit():
            continue
        out.append(token)
    return list(dict.fromkeys(out))[:8]


def _detect_should_persist(query: str) -> bool:
    q = (query or "").lower()
    return not any(p in q for p in NO_SAVE_PATTERNS)


def build_query_plan(
    query: str,
    default_domain: str,
    cfg_domains: dict[str, Any],
    venue_aliases: dict[str, list[str]],
) -> QueryPlan:
    raw_query = (query or "").strip()
    parsed = parse_query(raw_query, cfg_domains, venue_aliases)

    resolved_domain = parsed.domain or default_domain
    domain_cfg = cfg_domains.get(resolved_domain, {})
    domain_venues = [v for v in domain_cfg.get("venues", []) if isinstance(v, str)]
    target_venues = [parsed.venue] if parsed.venue else domain_venues

    year_start, year_end = _extract_year_range(raw_query)
    year = parsed.year if (year_start is None and year_end is None) else None

    removable_terms = list(domain_venues)
    removable_terms.extend([parsed.venue or "", resolved_domain, "ai", "ml"])
    for k, aliases in venue_aliases.items():
        removable_terms.append(k)
        removable_terms.extend(aliases or [])
    keywords = _extract_keywords(raw_query, removable_terms)

    if parsed.venue:
        source_query_text = f"{parsed.venue} {' '.join(keywords)}".strip()
    elif keywords:
        source_query_text = " ".join(keywords)
    else:
        source_query_text = " OR ".join(target_venues[:3])

    return QueryPlan(
        raw_query=raw_query,
        domain=resolved_domain,
        venue=parsed.venue,
        year=year,
        year_start=year_start,
        year_end=year_end,
        target_venues=target_venues,
        keywords=keywords,
        should_persist=_detect_should_persist(raw_query),
        source_query_text=source_query_text,
    )
