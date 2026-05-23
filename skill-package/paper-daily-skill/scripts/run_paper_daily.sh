#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${1:-ai}"
SOURCE="${2:-openalex}"
QUERY="${3:-}"

PROJECT_ROOT="/Users/lijiaxing/Documents/codex_workspace/paper-daily-mvp"
SKILL_HOME="/Users/lijiaxing/.codex/skills/paper-daily-skill"
SKILL_CONFIG_PATH="${SKILL_HOME}/config/skill.yaml"
SKILL_CREDENTIALS_PATH="${SKILL_HOME}/config/credentials.yaml"

cd "$PROJECT_ROOT"

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
