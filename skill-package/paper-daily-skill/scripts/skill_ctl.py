from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Unified skill controller: NL config update + scheduler install + optional run")
    p.add_argument("text", help="natural language command, e.g. 每天19点给我一个论文 / 停止定时任务")
    p.add_argument("--skill-config", default=str(Path.home() / ".codex/skills/paper-daily-skill/config/skill.yaml"))
    p.add_argument("--run-now", action="store_true", help="run one job immediately after update")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    update_cmd = [
        "python",
        str(project_root / "scripts/update_skill_config.py"),
        args.text,
        "--skill-config",
        args.skill_config,
    ]
    subprocess.run(update_cmd, cwd=project_root, check=True)

    install_cmd = [
        "python",
        str(project_root / "scripts/install_scheduler.py"),
        "--project-root",
        str(project_root),
        "--skill-config",
        args.skill_config,
    ]
    subprocess.run(install_cmd, cwd=project_root, check=True)

    if args.run_now:
        run_cmd = [
            "python",
            str(project_root / "scripts/run_from_skill_config.py"),
            "--skill-config",
            args.skill_config,
        ]
        if args.verbose:
            run_cmd.append("--verbose")
        subprocess.run(run_cmd, cwd=project_root, check=True)


if __name__ == "__main__":
    main()
