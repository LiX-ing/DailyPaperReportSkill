from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceCapability:
    name: str
    supports_query_text: bool
    supports_venue_filter: bool
    supports_year_filter: bool


CAPABILITIES: dict[str, SourceCapability] = {
    "openalex": SourceCapability(
        name="openalex",
        supports_query_text=False,
        supports_venue_filter=True,
        supports_year_filter=True,
    ),
    "semantic_scholar": SourceCapability(
        name="semantic_scholar",
        supports_query_text=True,
        supports_venue_filter=True,
        supports_year_filter=True,
    ),
    "openreview": SourceCapability(
        name="openreview",
        supports_query_text=False,
        supports_venue_filter=True,
        supports_year_filter=True,
    ),
}


def get_capability(source: str) -> SourceCapability:
    return CAPABILITIES.get(source, CAPABILITIES["openalex"])
