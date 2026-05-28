#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/fast-tools"
INSTALL_SCRIPT_URL="https://raw.githubusercontent.com/trungkien65/fast-tools/main/install.sh"
APP_BIN="${INSTALL_DIR}/fast-tools"
VERSION_FILE="${INSTALL_DIR}/version.json"
UNINSTALL_SCRIPT="${INSTALL_DIR}/uninstall.sh"

print_version() {
  if [[ ! -f "${VERSION_FILE}" ]]; then
    echo "unknown"
    return
  fi
  python3 - "${VERSION_FILE}" <<'PY'
import json
import sys
path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as f:
        print(json.load(f).get("version", "unknown"))
except Exception:
    print("unknown")
PY
}

if [[ "${1:-}" == "--version" ]]; then
  print_version
  exit 0
fi

if [[ "${1:-}" == "--update" ]]; then
  exec bash -c "curl -fsSL ${INSTALL_SCRIPT_URL} | bash"
fi

if [[ "${1:-}" == "--uninstall" ]]; then
  if [[ -x "${UNINSTALL_SCRIPT}" ]]; then
    exec "${UNINSTALL_SCRIPT}"
  fi
  echo "Uninstall script not found at ${UNINSTALL_SCRIPT}"
  exit 1
fi

if [[ ! -x "${APP_BIN}" ]]; then
  echo "Fast Tools binary not found at ${APP_BIN}"
  exit 1
fi

exec "${APP_BIN}" "$@"
