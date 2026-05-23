from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_skill_config


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run paper-daily job from skill.yaml schedule config")
    p.add_argument("--skill-config", default="config/skill.yaml")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--respect-time", action="store_true", help="Run only when now matches schedule.run_time in schedule.timezone")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = ROOT
    skill_config_path = Path(args.skill_config)
    if not skill_config_path.is_absolute():
        skill_config_path = root / skill_config_path

    cfg = load_skill_config(skill_config_path)
    schedule = cfg.schedule

    enabled = bool(schedule.get("enabled", False))
    if not enabled:
        print("Schedule disabled in skill config. Skip run.")
        return

    domain = str(schedule.get("domain", "ai")).strip() or "ai"
    source = str(schedule.get("source", "openalex")).strip() or "openalex"
    query = str(schedule.get("query", "")).strip()
    run_time = str(schedule.get("run_time", "")).strip()
    timezone = str(schedule.get("timezone", "Asia/Shanghai")).strip() or "Asia/Shanghai"

    if args.respect_time and run_time:
        try:
            hh, mm = run_time.split(":", 1)
            target_h = int(hh)
            target_m = int(mm)
            now = datetime.now(ZoneInfo(timezone))
            if now.hour != target_h or now.minute != target_m:
                print(
                    f"Outside scheduled time. now={now.strftime('%H:%M')} "
                    f"target={run_time} timezone={timezone}. Skip run."
                )
                return
        except Exception:
            print(f"Invalid schedule.run_time/timezone config: run_time={run_time}, timezone={timezone}")
            return

    cmd = [
        sys.executable,
        "-m",
        "src.main",
        "--domain",
        domain,
        "--source",
        source,
        "--skill-config",
        str(skill_config_path),
    ]
    if query:
        cmd.extend(["--query", query])
    if args.dry_run:
        cmd.append("--dry-run")
    if args.verbose:
        cmd.append("--verbose")

    print("Running scheduled job:", " ".join(cmd))
    subprocess.run(cmd, cwd=root, check=True)


if __name__ == "__main__":
    main()
