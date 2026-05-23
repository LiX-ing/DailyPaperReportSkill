from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.config import load_skill_config, load_venues_config


class ConfigTests(unittest.TestCase):
    def test_load_skill_config_reads_output_and_dedup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "skill.yaml"
            path.write_text(
                """
output:
  md_dir: output/md
  feishu_card_dir: output/feishu_cards
  formats: [markdown, feishu_card_json]
dedup:
  enabled: true
  skip_if_generated: true
""".strip(),
                encoding="utf-8",
            )
            cfg = load_skill_config(path)
            self.assertEqual(cfg.output["md_dir"], "output/md")
            self.assertIn("feishu_card_json", cfg.output["formats"])
            self.assertTrue(cfg.dedup["enabled"])

    def test_load_skill_config_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "skill.yaml"
            path.write_text(
                """
schedule:
  enabled: true
  domain: ai
  source: openalex
  query: ""
""".strip(),
                encoding="utf-8",
            )
            cfg = load_skill_config(path)
            self.assertTrue(cfg.schedule["enabled"])
            self.assertEqual(cfg.schedule["domain"], "ai")

    def test_load_venues_config_domains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "venues.yaml"
            path.write_text(
                """
domains:
  ai:
    venues: [NeurIPS]
selection:
  default_year_window: 2
venue_aliases:
  neurips: [Neural Information Processing Systems]
""".strip(),
                encoding="utf-8",
            )
            cfg = load_venues_config(path)
            self.assertIn("ai", cfg.domains)
            self.assertEqual(cfg.selection["default_year_window"], 2)
            self.assertIn("neurips", cfg.venue_aliases)


if __name__ == "__main__":
    unittest.main()
