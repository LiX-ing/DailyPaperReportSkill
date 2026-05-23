#!/usr/bin/env bash
set -euo pipefail

LABEL="com.lijiaxing.paper-daily-skill"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"

if [[ ! -f "$PLIST_PATH" ]]; then
  echo "Not installed: $PLIST_PATH"
  exit 0
fi

echo "Plist file exists: $PLIST_PATH"
launchctl list | rg "$LABEL" || echo "launchctl list: label not loaded"

echo "Next run time isn't directly exposed by launchd. Check logs after scheduled time:"
echo "  /Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp/logs/paper-daily-launchd.out.log"
echo "  /Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp/logs/paper-daily-launchd.err.log"
