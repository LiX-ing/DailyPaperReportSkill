#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-ai}"
SOURCE="${2:-openalex}"
QUERY="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_HOME="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_CONFIG_PATH="${SKILL_HOME}/config/skill.yaml"
SKILL_CREDENTIALS_PATH="${SKILL_HOME}/config/credentials.yaml"
LOCAL_ENV_PATH="${SKILL_HOME}/config/local.env"

if [[ -f "$LOCAL_ENV_PATH" ]]; then
  # shellcheck disable=SC1090
  source "$LOCAL_ENV_PATH"
fi

if [[ -n "${PAPER_DAILY_PROJECT_ROOT:-}" ]]; then
  PROJECT_ROOT="$PAPER_DAILY_PROJECT_ROOT"
elif [[ -f "$PWD/src/main.py" && -d "$PWD/scripts" ]]; then
  PROJECT_ROOT="$PWD"
else
  echo "Cannot locate paper-daily-mvp project root."
  echo "Run this script from project root, or set PAPER_DAILY_PROJECT_ROOT=/path/to/paper-daily-mvp."
  exit 1
fi

cd "$PROJECT_ROOT"

# Preflight: auto-heal writable runtime dirs for DB/output/logs.
mkdir -p data output logs
chmod -R u+rwX data output logs 2>/dev/null || true
chflags -R nouchg data output logs 2>/dev/null || true
xattr -dr com.apple.quarantine data output logs 2>/dev/null || true

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

export SKILL_CREDENTIALS_PATH

if [[ -n "$QUERY" ]]; then
  python -m src.main --domain "$DOMAIN" --source "$SOURCE" --query "$QUERY" --skill-config "$SKILL_CONFIG_PATH"
else
  python -m src.main --domain "$DOMAIN" --source "$SOURCE" --skill-config "$SKILL_CONFIG_PATH"
fi
