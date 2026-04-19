#!/usr/bin/env bash
set -euo pipefail

APP_ID=io.github.seulsale.PersistentClaudeCode
APP_NAME=persistent-claude-code
PREFIX="${HOME}/.local"
SHARE="${PREFIX}/share"
BIN="${PREFIX}/bin"

rm -f "${BIN}/${APP_NAME}"
rm -rf "${SHARE}/${APP_NAME}"
rm -f "${SHARE}/applications/${APP_ID}.desktop"
rm -f "${SHARE}/icons/hicolor/scalable/apps/${APP_ID}.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${SHARE}/applications" || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t -f "${SHARE}/icons/hicolor" || true
fi

echo "Uninstalled ${APP_NAME}"
