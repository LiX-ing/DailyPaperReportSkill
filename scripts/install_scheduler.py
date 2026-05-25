from __future__ import annotations

import argparse
import plistlib
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
    home = Path.home()
    protected_roots = [home / "Documents", home / "Desktop", home / "Downloads"]
    if any(root in project_root.parents or project_root == root for root in protected_roots):
        raise SystemExit(
            "project-root is under a protected macOS folder (Documents/Desktop/Downloads). "
            "Move the repo to e.g. ~/work/paper-daily-mvp and retry."
        )

    hh, mm = run_time.split(":", 1)
    hh_i, mm_i = int(hh), int(mm)
    label = "com.lijiaxing.paper-daily-skill"
    plist = home / "Library/LaunchAgents" / f"{label}.plist"
    logs = project_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    py_bin = project_root / ".venv/bin/python"
    if py_bin.exists():
        py = str(py_bin)
    else:
        py = "python3"

    cmd = (
        f"cd '{project_root}' && "
        f"{py} scripts/run_from_skill_config.py --skill-config '{skill_config}' --verbose"
    )
    plist_data = {
        "Label": label,
        "ProgramArguments": ["/bin/zsh", "-lc", cmd],
        "StartCalendarInterval": {"Hour": hh_i, "Minute": mm_i},
        "RunAtLoad": False,
        "WorkingDirectory": str(project_root),
        "StandardOutPath": str(logs / "paper-daily-launchd.out.log"),
        "StandardErrorPath": str(logs / "paper-daily-launchd.err.log"),
    }
    plist.parent.mkdir(parents=True, exist_ok=True)
    with plist.open("wb") as f:
        plistlib.dump(plist_data, f)

    uid = subprocess.check_output(["id", "-u"], text=True).strip()
    domain = f"gui/{uid}"
    subprocess.run(["plutil", "-lint", str(plist)], check=True)
    subprocess.run(["launchctl", "bootout", domain, str(plist)], check=False)
    subprocess.run(["launchctl", "bootstrap", domain, str(plist)], check=True)
    subprocess.run(["launchctl", "enable", f"{domain}/{label}"], check=False)
    print(f"Installed launchd job at {plist}")


def install_linux(project_root: Path, skill_config: Path, run_time: str) -> None:
    hh, mm = run_time.split(":", 1)
    cron_line = (
        f"{int(mm)} {int(hh)} * * * cd '{project_root}' && "
        f"if [ -d .venv ]; then . .venv/bin/activate; fi && "
        f"python scripts/run_from_skill_config.py --skill-config '{skill_config}' --verbose"
    )
    print("Run these commands on Linux:")
    print("(crontab -l 2>/dev/null; echo \"" + cron_line + "\") | crontab -")


def install_windows(project_root: Path, skill_config: Path, run_time: str) -> None:
    hh, mm = run_time.split(":", 1)
    task_name = "paper-daily-skill"
    cmd = (
        f'schtasks /Create /F /SC DAILY /TN "{task_name}" '
        f'/TR "python {project_root / "scripts/run_from_skill_config.py"} --skill-config {skill_config} --verbose" '
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
