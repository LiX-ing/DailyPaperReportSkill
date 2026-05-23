from __future__ import annotations

from dataclasses import dataclass

from .openalex_client import Paper
from .query_planner import QueryPlan


@dataclass
class ScoredPaper:
    paper: Paper
    score: float


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _venue_terms(plan: QueryPlan, venue_aliases: dict[str, list[str]]) -> list[str]:
    terms: list[str] = []
    if plan.venue:
        terms.append(plan.venue)
        terms.extend(venue_aliases.get(plan.venue, []))
        terms.extend(venue_aliases.get(plan.venue.lower(), []))
    else:
        terms.extend(plan.target_venues)
    out = [_norm(x) for x in terms if _norm(x)]
    return list(dict.fromkeys(out))


def score_paper(
    paper: Paper,
    plan: QueryPlan,
    venue_aliases: dict[str, list[str]],
) -> float:
    score = 0.0
    text = " ".join(
        [
            _norm(paper.title),
            _norm(paper.abstract),
            _norm(paper.venue),
            " ".join(_norm(v) for v in (paper.venue_candidates or [])),
        ]
    )

    if plan.year is not None:
        if paper.year == plan.year:
            score += 6.0
        else:
            score -= 2.0
    elif plan.year_start is not None and plan.year_end is not None:
        if plan.year_start <= paper.year <= plan.year_end:
            score += 4.0
        else:
            score -= 2.0

    terms = _venue_terms(plan, venue_aliases)
    if terms and any(term in text for term in terms):
        score += 6.0

    kw_hits = 0
    for kw in plan.keywords:
        if _norm(kw) in text:
            kw_hits += 1
    score += min(10.0, kw_hits * 2.0)

    if paper.abstract:
        score += 0.5
    return score


def rank_papers(
    papers: list[Paper],
    plan: QueryPlan,
    venue_aliases: dict[str, list[str]],
) -> list[ScoredPaper]:
    scored = [
        ScoredPaper(
            paper=p,
            score=score_paper(
                paper=p,
                plan=plan,
                venue_aliases=venue_aliases,
            ),
        )
        for p in papers
    ]
    scored.sort(
        key=lambda x: (
            -x.score,
            -int(x.paper.year or 0),
            x.paper.title.lower(),
        )
    )
    return scored
