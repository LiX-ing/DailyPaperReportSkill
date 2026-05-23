from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm import load_llm_settings


class LLMSettingsTests(unittest.TestCase):
    def test_reads_skill_vars_from_zshrc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".zshrc").write_text(
                """
export SKILL_BASE_URL=https://skill-endpoint.local/v1
export SKILL_AUTH_TOKEN=skill-token
export SKILL_MODEL=skill-model
""".strip(),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True), patch("pathlib.Path.home", return_value=home):
                settings = load_llm_settings(root=home)

            self.assertEqual(settings.provider, "openai_compatible")
            self.assertEqual(settings.base_url, "https://skill-endpoint.local/v1")
            self.assertEqual(settings.api_key, "skill-token")
            self.assertEqual(settings.model, "skill-model")

    def test_reads_anthropic_vars_from_zhsrc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".zhsrc").write_text(
                """
export ANTHROPIC_BASE_URL=https://example-compat.local/v1
export ANTHROPIC_AUTH_TOKEN=token-123
export ANTHROPIC_MODEL=claude-sonnet
""".strip(),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True), patch("pathlib.Path.home", return_value=home):
                settings = load_llm_settings()

            self.assertEqual(settings.provider, "openai_compatible")
            self.assertEqual(settings.base_url, "https://example-compat.local/v1")
            self.assertEqual(settings.api_key, "token-123")
            self.assertEqual(settings.model, "claude-sonnet")


if __name__ == "__main__":
    unittest.main()
