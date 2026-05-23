from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import yaml


def apply_natural_language(raw: dict, text: str) -> tuple[dict, list[str]]:
    cfg = dict(raw or {})
    cfg.setdefault("schedule", {})
    changes: list[str] = []
    t = text.strip().lower()

    if any(k in text for k in ["停止定时", "关闭定时", "暂停定时", "stop schedule", "disable schedule"]):
        cfg["schedule"]["enabled"] = False
        changes.append("schedule.enabled=false")

    m = re.search(r"每天\s*(\d{1,2})\s*点(?:(\d{1,2})分)?", text)
    if m:
        h = int(m.group(1))
        mm = int(m.group(2) or 0)
        cfg["schedule"]["enabled"] = True
        cfg["schedule"]["run_time"] = f"{h:02d}:{mm:02d}"
        changes.append(f"schedule.run_time={cfg['schedule']['run_time']}")

    if "不开飞书" in text or "关闭飞书" in text:
        cfg.setdefault("webhook", {})
        cfg["webhook"]["enabled"] = False
        changes.append("webhook.enabled=false")
    if "开飞书" in text or "开启飞书" in text:
        cfg.setdefault("webhook", {})
        cfg["webhook"]["enabled"] = True
        changes.append("webhook.enabled=true")

    return cfg, changes


def append_history(history_path: Path, text: str, changes: list[str]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = [f"## {now}", f"- request: {text}"]
    for c in changes:
        entry.append(f"- change: {c}")
    entry.append("")
    if history_path.exists():
        old = history_path.read_text(encoding="utf-8")
    else:
        old = "# Config Change History\n\n"
    history_path.write_text(old + "\n".join(entry), encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser(description="Update skill.yaml by natural language command")
    p.add_argument("text", help="natural language request")
    p.add_argument("--skill-config", default=str(Path.home() / ".codex/skills/paper-daily-skill/config/skill.yaml"))
    p.add_argument("--history", default="docs/config_history.md")
    args = p.parse_args()

    cfg_path = Path(args.skill_config).resolve()
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    updated, changes = apply_natural_language(raw, args.text)
    if not changes:
        print("No recognized config intent; nothing changed.")
        return
    cfg_path.write_text(yaml.safe_dump(updated, allow_unicode=True, sort_keys=False), encoding="utf-8")

    project_root = Path(__file__).resolve().parents[1]
    history_path = Path(args.history)
    if not history_path.is_absolute():
        history_path = project_root / history_path
    append_history(history_path, args.text, changes)

    print("Updated:")
    for c in changes:
        print("-", c)
    print("Skill config:", cfg_path)
    print("History:", history_path)


if __name__ == "__main__":
    main()
