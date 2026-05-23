from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.storage import SeenPaperStore


class StorageTests(unittest.TestCase):
    def test_generated_record_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "seen.db"
            store = SeenPaperStore(db_path)
            try:
                self.assertFalse(store.was_generated("p1"))
                store.add_generated_record(
                    paper_id="p1",
                    title="paper",
                    source="openalex",
                    md_path="output/md/p1.md",
                    feishu_card_path="output/feishu/p1.json",
                    status="success",
                )
                self.assertTrue(store.was_generated("p1"))
            finally:
                store.close()

    def test_failed_record_does_not_count_as_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "seen.db"
            store = SeenPaperStore(db_path)
            try:
                store.add_generated_record(
                    paper_id="p2",
                    title="paper2",
                    source="openalex",
                    md_path=None,
                    feishu_card_path=None,
                    status="failed",
                )
                self.assertFalse(store.was_generated("p2"))
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
