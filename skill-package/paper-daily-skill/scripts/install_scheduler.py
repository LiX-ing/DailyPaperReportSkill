from __future__ import annotations

import argparse
import platform
import subprocess
from pathlib import Path


def read_schedule(skill_config: Path) -> tuple[bool, str, str]:
    import yaml

    data = yaml.safe_load(skill_config.read_text(encoding="utf-8")) or {}
    schedule = data.get("schedule", {}) if isinstance(data, dict) else {}
    enabled = bool(schedule.get("enabled", False))
    run_time = str(schedule.get("run_time", "07:00"))
    timezone = str(schedule.get("timezone", "Asia/Shanghai"))
    if isinstance(schedule.get("run_time"), int):
        rt = int(schedule["run_time"])
        run_time = f"{max(0,min(23,rt//60)):02d}:{max(0,min(59,rt%60)):02d}"
    return enabled, run_time, timezone


def install_macos(project_root: Path, skill_config: Path, run_time: str) -> None:
    hh, mm = run_time.split(":", 1)
    hh_i, mm_i = int(hh), int(mm)
    label = "com.lijiaxing.paper-daily-skill"
    plist = Path.home() / "Library/LaunchAgents" / f"{label}.plist"
    logs = project_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)

    cmd = (
        f"cd '{project_root}' && "
        f"if [ -d .venv ]; then source .venv/bin/activate; fi && "
        f"python scripts/run_from_skill_config.py --skill-config '{skill_config}' --respect-time --verbose"
    )
    plist.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>{label}</string>
<key>ProgramArguments</key><array><string>/bin/zsh</string><string>-lc</string><string>{cmd}</string></array>
<key>StartCalendarInterval</key><dict><key>Hour</key><integer>{hh_i}</integer><key>Minute</key><integer>{mm_i}</integer></dict>
<key>RunAtLoad</key><false/>
<key>WorkingDirectory</key><string>{project_root}</string>
<key>StandardOutPath</key><string>{logs / 'paper-daily-launchd.out.log'}</string>
<key>StandardErrorPath</key><string>{logs / 'paper-daily-launchd.err.log'}</string>
</dict></plist>''',
        encoding="utf-8",
    )
    subprocess.run(["launchctl", "unload", str(plist)], check=False)
    subprocess.run(["launchctl", "load", str(plist)], check=True)
    print(f"Installed launchd job at {plist}")


def install_linux(project_root: Path, skill_config: Path, run_time: str) -> None:
    hh, mm = run_time.split(":", 1)
    cron_line = (
        f"{int(mm)} {int(hh)} * * * cd '{project_root}' && "
        f"if [ -d .venv ]; then . .venv/bin/activate; fi && "
        f"python scripts/run_from_skill_config.py --skill-config '{skill_config}' --respect-time --verbose"
    )
    print("Run these commands on Linux:")
    print("(crontab -l 2>/dev/null; echo \"" + cron_line + "\") | crontab -")


def install_windows(project_root: Path, skill_config: Path, run_time: str) -> None:
    hh, mm = run_time.split(":", 1)
    task_name = "paper-daily-skill"
    cmd = (
        f'schtasks /Create /F /SC DAILY /TN "{task_name}" '
        f'/TR "python {project_root / "scripts/run_from_skill_config.py"} --skill-config {skill_config} --respect-time --verbose" '
        f'/ST {int(hh):02d}:{int(mm):02d}'
    )
    print("Run this command in Windows CMD as your user:")
    print(cmd)


def main() -> None:
    p = argparse.ArgumentParser(description="Install scheduler from skill.yaml")
    p.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    p.add_argument("--skill-config", default=str(Path.home() / ".codex/skills/paper-daily-skill/config/skill.yaml"))
    args = p.parse_args()

    project_root = Path(args.project_root).resolve()
    skill_config = Path(args.skill_config).resolve()
    if not skill_config.exists():
        raise SystemExit(f"skill config not found: {skill_config}")

    enabled, run_time, timezone = read_schedule(skill_config)
    if not enabled:
        print("schedule.enabled is false; skip installation")
        return
    print(f"schedule: {run_time} ({timezone})")

    sysname = platform.system().lower()
    if "darwin" in sysname:
        install_macos(project_root, skill_config, run_time)
    elif "linux" in sysname:
        install_linux(project_root, skill_config, run_time)
    elif "windows" in sysname:
        install_windows(project_root, skill_config, run_time)
    else:
        print(f"Unsupported OS: {platform.system()}")


if __name__ == "__main__":
    main()
