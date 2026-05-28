#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/fast-tools"
BACKUP_DIR="/opt/fast-tools.backup"
BIN_LINK="/usr/local/bin/fast-tools"
DESKTOP_FILE="/usr/share/applications/fast-tools.desktop"
ICON_FILE="/usr/share/icons/hicolor/256x256/apps/fast-tools.png"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

log() {
  echo "[INFO] $*"
}

log "Removing Fast Tools from system..."
${SUDO} rm -rf "${INSTALL_DIR}"
${SUDO} rm -rf "${BACKUP_DIR}"
${SUDO} rm -f "${BIN_LINK}"
${SUDO} rm -f "${DESKTOP_FILE}"
${SUDO} rm -f "${ICON_FILE}"

if command -v update-desktop-database >/dev/null 2>&1; then
  ${SUDO} update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  ${SUDO} gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi

log "Fast Tools removed."
