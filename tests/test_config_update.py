from __future__ import annotations

import unittest

from scripts.update_skill_config import apply_natural_language


class ConfigUpdateTests(unittest.TestCase):
    def test_disable_schedule(self) -> None:
        cfg, changes = apply_natural_language({"schedule": {"enabled": True}}, "我想让你停止定时任务")
        self.assertFalse(cfg["schedule"]["enabled"])
        self.assertIn("schedule.enabled=false", changes)

    def test_set_daily_time(self) -> None:
        cfg, changes = apply_natural_language({}, "每天19点给我一个论文")
        self.assertTrue(cfg["schedule"]["enabled"])
        self.assertEqual(cfg["schedule"]["run_time"], "19:00")
        self.assertIn("schedule.run_time=19:00", changes)


if __name__ == "__main__":
    unittest.main()
