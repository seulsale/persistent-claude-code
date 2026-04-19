#!/usr/bin/env bash
set -euo pipefail

APP_ID=io.github.seulsale.PersistentClaudeCode
APP_NAME=persistent-claude-code
PREFIX="${HOME}/.local"
SHARE="${PREFIX}/share"
BIN="${PREFIX}/bin"
REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

REQUIRED_PACMAN_PKGS=(python python-gobject gtk4 libadwaita vte4 webkitgtk-6.0 ttf-jetbrains-mono)

missing=()
for pkg in "${REQUIRED_PACMAN_PKGS[@]}"; do
  if ! pacman -Qq "${pkg}" >/dev/null 2>&1; then
    missing+=("${pkg}")
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo "Missing Arch packages: ${missing[*]}" >&2
  echo "Install with: sudo pacman -S ${missing[*]}" >&2
  exit 1
fi

py_version="$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if [[ "$(printf '%s\n3.14\n' "${py_version}" | sort -V | head -n1)" != "3.14" ]]; then
  echo "Python >= 3.14 required (found ${py_version})" >&2
  exit 1
fi

install -d "${SHARE}/${APP_NAME}"
cp -r "${REPO_ROOT}/src/persistent_claude_code" "${SHARE}/${APP_NAME}/"

install -d "${BIN}"
cat > "${BIN}/${APP_NAME}" <<EOF
#!/usr/bin/env bash
exec python3 -c 'import sys; sys.path.insert(0, "${SHARE}/${APP_NAME}"); from persistent_claude_code.__main__ import main; raise SystemExit(main())' "\$@"
EOF
chmod +x "${BIN}/${APP_NAME}"

install -Dm644 "${REPO_ROOT}/data/${APP_ID}.desktop" "${SHARE}/applications/${APP_ID}.desktop"
install -Dm644 "${REPO_ROOT}/data/${APP_ID}.svg" "${SHARE}/icons/hicolor/scalable/apps/${APP_ID}.svg"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${SHARE}/applications" || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -q -t -f "${SHARE}/icons/hicolor" || true
fi

echo "Installed ${APP_NAME} to ${PREFIX}"
echo "Launch from the app grid or run: ${APP_NAME}"
