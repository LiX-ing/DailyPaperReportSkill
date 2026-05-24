#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_CONFIG="${SKILL_CONFIG_PATH:-$HOME/.codex/skills/paper-daily-skill/config/skill.yaml}"
SKILL_HOME="${SKILL_HOME:-$HOME/.codex/skills/paper-daily-skill}"
PLIST_PATH="$HOME/Library/LaunchAgents/com.lijiaxing.paper-daily-skill.plist"
LOG_DIR="$PROJECT_ROOT/logs"
OUT_LOG="$LOG_DIR/paper-daily-launchd.out.log"
ERR_LOG="$LOG_DIR/paper-daily-launchd.err.log"

mkdir -p "$LOG_DIR"

if [[ ! -f "$SKILL_CONFIG" ]]; then
  echo "Skill config not found: $SKILL_CONFIG"
  exit 1
fi

case "$PROJECT_ROOT" in
  "$HOME/Documents"/*|"$HOME/Desktop"/*|"$HOME/Downloads"/*)
    echo "Project root is under a protected macOS folder: $PROJECT_ROOT"
    echo "Move repo to a non-protected path (e.g. \$HOME/work/paper-daily-mvp), then re-run setup."
    exit 2
    ;;
esac

RUN_TIME="$(SKILL_CONFIG="$SKILL_CONFIG" python - <<'PY'
import os
from pathlib import Path
import yaml
p = Path(os.environ["SKILL_CONFIG"])
c = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
s = c.get('schedule', {}) if isinstance(c, dict) else {}
rt = s.get('run_time','07:00')
if isinstance(rt, int):
    h = max(0, min(23, rt // 60))
    m = max(0, min(59, rt % 60))
    print(f"{h:02d}:{m:02d}")
else:
    print(str(rt))
PY
)"

if [[ ! "$RUN_TIME" =~ ^[0-9]{1,2}:[0-9]{2}$ ]]; then
  echo "Invalid schedule.run_time in $SKILL_CONFIG: $RUN_TIME"
  exit 1
fi

HOUR="${RUN_TIME%%:*}"
MIN="${RUN_TIME##*:}"
HOUR="$(printf '%d' "$HOUR")"
MIN="$(printf '%d' "$MIN")"

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  PY_BIN="$PROJECT_ROOT/.venv/bin/python"
else
  PY_BIN="$(command -v python3 || true)"
fi
if [[ -z "$PY_BIN" ]]; then
  echo "python3 not found and .venv python missing. Please install python3."
  exit 3
fi

CMD="cd '$PROJECT_ROOT' && SKILL_HOME='$SKILL_HOME' '$PY_BIN' scripts/run_from_skill_config.py --skill-config '$SKILL_CONFIG' --respect-time --verbose"
CMD_XML="${CMD//&/&amp;}"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.lijiaxing.paper-daily-skill</string>

  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-lc</string>
    <string>$CMD_XML</string>
  </array>

  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>$HOUR</integer>
    <key>Minute</key>
    <integer>$MIN</integer>
  </dict>

  <key>RunAtLoad</key>
  <false/>

  <key>WorkingDirectory</key>
  <string>$PROJECT_ROOT</string>

  <key>StandardOutPath</key>
  <string>$OUT_LOG</string>
  <key>StandardErrorPath</key>
  <string>$ERR_LOG</string>
</dict>
</plist>
PLIST

plutil -lint "$PLIST_PATH" >/dev/null
launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "gui/$(id -u)/com.lijiaxing.paper-daily-skill" >/dev/null 2>&1 || true

echo "Installed launchd job: com.lijiaxing.paper-daily-skill"
echo "Schedule: daily at $RUN_TIME (system local timezone)"
echo "Plist: $PLIST_PATH"
echo "Logs:"
echo "  $OUT_LOG"
echo "  $ERR_LOG"
