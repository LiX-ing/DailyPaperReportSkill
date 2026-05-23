from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.openalex_client import Paper
from src.report import write_feishu_card_json, write_markdown_report


class ReportTests(unittest.TestCase):
    def _paper(self) -> Paper:
        return Paper(
            paper_id="p1",
            title="Test Paper",
            abstract="abstract",
            year=2026,
            venue="NeurIPS",
            venue_candidates=["NeurIPS"],
            doi="10.1/abc",
            url="https://example.com/p1",
        )

    def test_markdown_report_only_has_structured_card_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_markdown_report(
                out_dir=Path(tmp),
                paper=self._paper(),
                summary={"card_markdown": "### 基础信息\n- 中文标题: 测试标题"},
                domain="ai",
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn("# 结构化速读卡片（ai）", content)
            self.assertIn("### 基础信息", content)
            self.assertNotIn("## 中文简版", content)

    def test_feishu_card_json_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_feishu_card_json(
                out_dir=Path(tmp),
                paper=self._paper(),
                summary={
                    "zh_title": "测试标题",
                    "zh_abstract": "测试摘要",
                    "key_points": "1) 点1",
                    "decision": "建议精读",
                },
                domain="ai",
            )
            obj = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(obj["schema_version"], "v1")
            self.assertEqual(obj["paper"]["paper_id"], "p1")
            self.assertIn("基础信息", obj["card"])


if __name__ == "__main__":
    unittest.main()
