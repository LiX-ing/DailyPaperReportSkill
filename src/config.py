from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class VenuesConfig:
    raw: dict[str, Any]

    @property
    def domains(self) -> dict[str, Any]:
        return self.raw.get("domains", {})

    @property
    def selection(self) -> dict[str, Any]:
        return self.raw.get("selection", {})

    @property
    def venue_aliases(self) -> dict[str, list[str]]:
        return self.raw.get("venue_aliases", {})


@dataclass
class SkillConfig:
    raw: dict[str, Any]

    @property
    def output(self) -> dict[str, Any]:
        return self.raw.get("output", {})

    @property
    def dedup(self) -> dict[str, Any]:
        return self.raw.get("dedup", {})

    @property
    def webhook(self) -> dict[str, Any]:
        return self.raw.get("webhook", {})

    @property
    def schedule(self) -> dict[str, Any]:
        return self.raw.get("schedule", {})


def load_venues_config(path: Path) -> VenuesConfig:
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return VenuesConfig(raw=raw or {})


def load_skill_config(path: Path) -> SkillConfig:
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return SkillConfig(raw=raw or {})


def load_config(path: Path) -> VenuesConfig:
    # Backward-compatible alias.
    return load_venues_config(path)
