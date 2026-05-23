#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp"
SKILL_CONFIG="/Users/lijiaxing/.codex/skills/paper-daily-skill/config/skill.yaml"
PLIST_PATH="$HOME/Library/LaunchAgents/com.lijiaxing.paper-daily-skill.plist"
LOG_DIR="$PROJECT_ROOT/logs"
OUT_LOG="$LOG_DIR/paper-daily-launchd.out.log"
ERR_LOG="$LOG_DIR/paper-daily-launchd.err.log"

mkdir -p "$LOG_DIR"

if [[ ! -f "$SKILL_CONFIG" ]]; then
  echo "Skill config not found: $SKILL_CONFIG"
  exit 1
fi

RUN_TIME="$(python - <<'PY'
from pathlib import Path
import yaml
p = Path('/Users/lijiaxing/.codex/skills/paper-daily-skill/config/skill.yaml')
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

CMD="cd '$PROJECT_ROOT' && if [ -d .venv ]; then source .venv/bin/activate; fi && python scripts/run_from_skill_config.py --skill-config '$SKILL_CONFIG' --respect-time --verbose"

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
    <string>$CMD</string>
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

launchctl unload "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl load "$PLIST_PATH"

echo "Installed launchd job: com.lijiaxing.paper-daily-skill"
echo "Schedule: daily at $RUN_TIME (system local timezone)"
echo "Plist: $PLIST_PATH"
echo "Logs:"
echo "  $OUT_LOG"
echo "  $ERR_LOG"
