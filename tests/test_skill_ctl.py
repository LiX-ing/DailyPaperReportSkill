from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


def _load_skill_ctl_module():
    root = Path(__file__).resolve().parents[1]
    mod_path = root / "scripts" / "skill_ctl.py"
    spec = importlib.util.spec_from_file_location("skill_ctl", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SkillCtlTests(unittest.TestCase):
    @patch("subprocess.run")
    def test_runs_update_and_install(self, mock_run):
        skill_ctl = _load_skill_ctl_module()
        with patch("argparse.ArgumentParser.parse_args") as parse_args:
            class A:
                text = "每天19点给我一个论文"
                skill_config = "/tmp/skill.yaml"
                run_now = False
                verbose = False
            parse_args.return_value = A()
            skill_ctl.main()
        self.assertGreaterEqual(mock_run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
