#!/usr/bin/env bash
set -euo pipefail

PKG_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PKG_DIR"

LATEST_TAR="$(ls -t paper-daily-skill-package-*.tar.gz 2>/dev/null | head -n 1 || true)"
if [[ -z "$LATEST_TAR" ]]; then
  echo "No package found: paper-daily-skill-package-*.tar.gz"
  exit 1
fi

echo "Using package: $LATEST_TAR"

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

tar -xzf "$LATEST_TAR" -C "$tmpdir"

SRC="$tmpdir/paper-daily-skill"
DST="$HOME/.codex/skills/paper-daily-skill"
mkdir -p "$DST"
rsync -a --delete "$SRC/" "$DST/"

echo "Installed to: $DST"
echo "Current config:"
cat "$DST/config/skill.yaml"
