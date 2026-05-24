#!/usr/bin/env bash
set -euo pipefail

LABEL="com.lijiaxing.paper-daily-skill"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [[ ! -f "$PLIST_PATH" ]]; then
  echo "Not installed: $PLIST_PATH"
  exit 0
fi

echo "Plist file exists: $PLIST_PATH"
launchctl list | grep "$LABEL" || echo "launchctl list: label not loaded"

echo "Next run time isn't directly exposed by launchd. Check logs after scheduled time:"
echo "  $PROJECT_ROOT/logs/paper-daily-launchd.out.log"
echo "  $PROJECT_ROOT/logs/paper-daily-launchd.err.log"
