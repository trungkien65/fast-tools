#!/usr/bin/env bash
set -Eeuo pipefail

INSTALL_DIR="/opt/fast-tools"
INSTALL_SCRIPT_URL="https://raw.githubusercontent.com/trungkien65/fast-tools/main/install.sh"
APP_BIN="${INSTALL_DIR}/fast-tools"
VERSION_FILE="${INSTALL_DIR}/version.json"
UNINSTALL_SCRIPT="${INSTALL_DIR}/uninstall.sh"

read_metadata_field() {
  local field="$1"
  local fallback="$2"
  if [[ ! -f "${VERSION_FILE}" ]]; then
    echo "${fallback}"
    return
  fi

  python3 - "${VERSION_FILE}" "${field}" "${fallback}" <<'PY'
import json
import sys
path, field, fallback = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    value = str(data.get(field, "")).strip()
    if field == "channel":
        value = value.lower()
        if value not in {"stable", "beta"}:
            value = ""
    print(value or fallback)
except Exception:
    print(fallback)
PY
}

run_installer() {
  local channel="$1"
  shift || true
  curl -fsSL "${INSTALL_SCRIPT_URL}" | bash -s -- --channel "${channel}" "$@"
}

case "${1:-}" in
  --version)
    read_metadata_field "version" "unknown"
    exit 0
    ;;
  --channel)
    read_metadata_field "channel" "stable"
    exit 0
    ;;
  --update)
    current_channel="$(read_metadata_field "channel" "stable")"
    run_installer "${current_channel}" --update
    exit 0
    ;;
  --switch-channel)
    if [[ -z "${2:-}" ]]; then
      echo "Missing channel. Use: --switch-channel stable|beta" >&2
      exit 1
    fi
    target_channel="${2}"
    if [[ "${target_channel}" != "stable" && "${target_channel}" != "beta" ]]; then
      echo "Invalid channel: ${target_channel}. Use stable|beta" >&2
      exit 1
    fi
    run_installer "${target_channel}" --update --force
    exit 0
    ;;
  --uninstall)
    if [[ -x "${UNINSTALL_SCRIPT}" ]]; then
      exec "${UNINSTALL_SCRIPT}"
    fi
    echo "Uninstall script not found at ${UNINSTALL_SCRIPT}" >&2
    exit 1
    ;;
  -h|--help)
    cat <<'USAGE'
Fast Tools wrapper

Commands:
  --version                 Print installed version
  --channel                 Print current update channel
  --update                  Update using installed channel
  --switch-channel <name>   Switch to stable|beta then update
  --uninstall               Remove Fast Tools
USAGE
    exit 0
    ;;
esac

if [[ ! -x "${APP_BIN}" ]]; then
  echo "Fast Tools binary not found at ${APP_BIN}" >&2
  exit 1
fi

exec "${APP_BIN}" "$@"
