from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.llm import load_llm_settings


class LLMCredentialsFileTests(unittest.TestCase):
    def test_reads_credentials_yaml_when_env_and_shell_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_dir = root / "config"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "credentials.yaml").write_text(
                """
llm:
  provider: openai_compatible
  model: glm-5-turbo
  api_key: test-token
  base_url: http://127.0.0.1:9999/v1
""".strip(),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True), patch("pathlib.Path.home", return_value=root):
                settings = load_llm_settings(root=root)

            self.assertEqual(settings.provider, "openai_compatible")
            self.assertEqual(settings.model, "glm-5-turbo")
            self.assertEqual(settings.api_key, "test-token")
            self.assertEqual(settings.base_url, "http://127.0.0.1:9999/v1")

    def test_credentials_file_has_higher_priority_than_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg_dir = root / "config"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            (cfg_dir / "credentials.yaml").write_text(
                """
llm:
  provider: openai_compatible
  model: from-file
  api_key: file-token
  base_url: http://file-endpoint/v1
""".strip(),
                encoding="utf-8",
            )
            env = {
                "SKILL_MODEL": "from-env",
                "SKILL_AUTH_TOKEN": "env-token",
                "SKILL_BASE_URL": "http://env-endpoint/v1",
            }
            with patch.dict(os.environ, env, clear=True), patch("pathlib.Path.home", return_value=root):
                settings = load_llm_settings(root=root)

            self.assertEqual(settings.model, "from-file")
            self.assertEqual(settings.api_key, "file-token")
            self.assertEqual(settings.base_url, "http://file-endpoint/v1")


if __name__ == "__main__":
    unittest.main()
