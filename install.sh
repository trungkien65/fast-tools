#!/usr/bin/env bash
set -Eeuo pipefail

GITHUB_OWNER="trungkien65"
GITHUB_REPO="fast-tools"
APP_BIN_NAME="fast-tools"
INSTALL_DIR="/opt/fast-tools"
BIN_LINK="/usr/local/bin/fast-tools"
DESKTOP_FILE="/usr/share/applications/fast-tools.desktop"
ICON_DEST_HICOLOR="/usr/share/icons/hicolor/256x256/apps/fast-tools.png"
BACKUP_DIR="/opt/fast-tools.backup"
INSTALL_REF="${FAST_TOOLS_INSTALL_REF:-main}"
RAW_BASE_URL="https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${INSTALL_REF}"
LATEST_STABLE_API_URL="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest"
ALL_RELEASES_API_URL="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases"
UNINSTALL_URL="${RAW_BASE_URL}/uninstall.sh"
INSTALL_SCRIPT_URL="${RAW_BASE_URL}/install.sh"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

log() {
  echo "[INFO] $*"
}

err() {
  echo "[ERROR] $*" >&2
}

usage() {
  cat <<'USAGE'
Usage: install.sh [OPTIONS]

Options:
  --beta                Install using beta channel (latest prerelease)
  --channel <name>      Select release channel: stable|beta
  --update              Perform channel-aware update
  --force               Force reinstall even when version is unchanged
  -h, --help            Show this help
USAGE
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    err "Missing required command: $1"
    exit 1
  fi
}

detect_os() {
  if [[ ! -f /etc/os-release ]]; then
    err "Cannot detect OS: /etc/os-release missing"
    exit 1
  fi

  # shellcheck disable=SC1091
  source /etc/os-release
  local family="${ID_LIKE:-}"
  local distro="${ID:-}"
  if [[ "${distro}" != "ubuntu" && "${distro}" != "debian" && "${distro}" != "linuxmint" && "${family}" != *"debian"* ]]; then
    err "Unsupported OS: ${PRETTY_NAME:-unknown}. This installer supports Ubuntu/Debian/Linux Mint."
    exit 1
  fi
  log "Detected OS: ${PRETTY_NAME:-$distro}"
}

detect_arch() {
  local machine
  machine="$(uname -m)"
  case "${machine}" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *)
      err "Unsupported architecture: ${machine}. Supported: amd64, arm64."
      exit 1
      ;;
  esac
  log "Detected architecture: ${ARCH}"
}

normalize_channel() {
  local value="${1:-stable}"
  case "${value}" in
    stable|beta)
      echo "${value}"
      ;;
    *)
      err "Invalid channel: ${value}. Use stable or beta."
      exit 1
      ;;
  esac
}

read_local_metadata() {
  local version_file="${INSTALL_DIR}/version.json"
  if [[ ! -f "${version_file}" ]]; then
    echo ""
    echo "stable"
    return
  fi

  python3 - "${version_file}" <<'PY'
import json
import sys
path = sys.argv[1]
version = ""
channel = "stable"
try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    version = str(data.get("version", "")).strip()
    parsed_channel = str(data.get("channel", "stable")).strip().lower()
    if parsed_channel in {"stable", "beta"}:
        channel = parsed_channel
except Exception:
    pass
print(version)
print(channel)
PY
}

fetch_release_json() {
  local url="$1"
  local headers_file="$2"
  local body_file="$3"

  if ! curl -sS -D "${headers_file}" -o "${body_file}" "${url}"; then
    err "Failed to call GitHub Releases API: ${url}"
    exit 1
  fi

  local status
  status="$(python3 - "${headers_file}" <<'PY'
import sys
path = sys.argv[1]
status_code = ""
with open(path, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        if line.startswith("HTTP/"):
            parts = line.strip().split()
            if len(parts) >= 2:
                status_code = parts[1]
print(status_code)
PY
)"

  if [[ "${status}" != "200" ]]; then
    local rate_remaining
    rate_remaining="$(python3 - "${headers_file}" <<'PY'
import sys
path = sys.argv[1]
remaining = ""
with open(path, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        key = line.split(":", 1)[0].strip().lower()
        if key == "x-ratelimit-remaining":
            remaining = line.split(":", 1)[1].strip()
print(remaining)
PY
)"
    if [[ "${rate_remaining}" == "0" ]]; then
      err "GitHub API rate limit exceeded. Try again later."
    else
      err "GitHub API returned HTTP ${status}."
    fi
    exit 1
  fi
}

extract_release_metadata() {
  local mode="$1"
  python3 - "${RELEASE_JSON_FILE}" "${ARCH}" "${mode}" <<'PY'
import json
import re
import sys

path, arch, mode = sys.argv[1], sys.argv[2], sys.argv[3]

with open(path, "r", encoding="utf-8") as f:
    payload = json.load(f)


def parse_version(tag_name: str):
    version = tag_name[1:] if tag_name.startswith("v") else tag_name
    version = version.split("+", 1)[0]
    if "-" in version:
        core, pre = version.split("-", 1)
        pre_parts = pre.split(".")
    else:
        core, pre_parts = version, []
    nums = []
    for piece in core.split("."):
        m = re.match(r"^(\d+)", piece)
        nums.append(int(m.group(1)) if m else 0)
    while len(nums) < 3:
        nums.append(0)
    return nums, pre_parts


def compare_pre(a_parts, b_parts):
    if not a_parts and not b_parts:
        return 0
    if not a_parts:
        return 1
    if not b_parts:
        return -1
    for idx in range(max(len(a_parts), len(b_parts))):
        if idx >= len(a_parts):
            return -1
        if idx >= len(b_parts):
            return 1
        a = a_parts[idx]
        b = b_parts[idx]
        a_num = a.isdigit()
        b_num = b.isdigit()
        if a_num and b_num:
            ai, bi = int(a), int(b)
            if ai != bi:
                return 1 if ai > bi else -1
            continue
        if a_num and not b_num:
            return -1
        if b_num and not a_num:
            return 1
        if a != b:
            return 1 if a > b else -1
    return 0


def compare_release(a, b):
    a_tag = str(a.get("tag_name", "")).strip()
    b_tag = str(b.get("tag_name", "")).strip()
    if not a_tag:
        return -1
    if not b_tag:
        return 1
    a_core, a_pre = parse_version(a_tag)
    b_core, b_pre = parse_version(b_tag)
    if a_core != b_core:
        return 1 if a_core > b_core else -1
    return compare_pre(a_pre, b_pre)


if mode == "stable_latest":
    releases = [payload]
elif mode == "beta_prerelease_only":
    releases = [r for r in payload if not r.get("draft", False) and r.get("prerelease", False)]
elif mode == "beta_any":
    releases = [r for r in payload if not r.get("draft", False)]
else:
    raise SystemExit(f"Unsupported mode: {mode}")

if not releases:
    if mode == "beta_prerelease_only":
        raise SystemExit("No prerelease found for beta channel.")
    raise SystemExit("No release candidates found.")

best = releases[0]
for candidate in releases[1:]:
    if compare_release(candidate, best) > 0:
        best = candidate

tag_name = str(best.get("tag_name", "")).strip()
if not tag_name:
    raise SystemExit("Release tag is missing from GitHub API response")
version = tag_name[1:] if tag_name.startswith("v") else tag_name
asset_name = f"fast-tools-linux-{arch}-v{version}.tar.gz"
checksum_name = f"{asset_name}.sha256"
archive_url = ""
checksum_url = ""
for asset in best.get("assets", []):
    name = str(asset.get("name", ""))
    if name == asset_name:
        archive_url = str(asset.get("browser_download_url", ""))
    elif name == checksum_name:
        checksum_url = str(asset.get("browser_download_url", ""))
if not archive_url:
    raise SystemExit(f"Release asset not found: {asset_name}")
if not checksum_url:
    raise SystemExit(f"Checksum asset not found: {checksum_name}")

print(version)
print(archive_url)
print(checksum_url)
print(tag_name)
print("true" if bool(best.get("prerelease", False)) else "false")
PY
}

write_wrapper_template() {
  local wrapper_file
  wrapper_file="$(mktemp)"

  cat > "${wrapper_file}" <<'WRAPPER'
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
WRAPPER

  cat "${wrapper_file}"
  rm -f "${wrapper_file}"
}

write_wrapper() {
  local wrapper_file
  wrapper_file="$(mktemp)"
  write_wrapper_template > "${wrapper_file}"
  ${SUDO} install -m 0755 "${wrapper_file}" "${BIN_LINK}"
  rm -f "${wrapper_file}"
}

write_desktop_entry() {
  local desktop_tmp
  desktop_tmp="$(mktemp)"
  cat > "${desktop_tmp}" <<EOF
[Desktop Entry]
Name=Fast Tools
Comment=Fast Tools desktop app
Exec=${BIN_LINK}
Icon=${INSTALL_DIR}/icon.png
Terminal=false
Type=Application
Categories=Development;Utility;
StartupNotify=true
EOF
  ${SUDO} install -m 0644 "${desktop_tmp}" "${DESKTOP_FILE}"
  rm -f "${desktop_tmp}"
}

copy_icon_if_present() {
  local icon_src="${INSTALL_DIR}/icon.png"
  if [[ -f "${icon_src}" ]]; then
    ${SUDO} mkdir -p "$(dirname "${ICON_DEST_HICOLOR}")"
    ${SUDO} cp -f "${icon_src}" "${ICON_DEST_HICOLOR}"
    log "Icon installed."
  else
    log "Icon not found in release package, skipping icon install."
  fi
}

verify_checksum() {
  local archive_file="$1"
  local checksum_file="$2"
  local checksum_url="$3"

  log "Downloading checksum: ${checksum_url}"
  curl -fsSL "${checksum_url}" -o "${checksum_file}"

  local expected_sha
  expected_sha="$(python3 - "${checksum_file}" <<'PY'
import re
import sys
path = sys.argv[1]
text = open(path, "r", encoding="utf-8", errors="replace").read()
m = re.search(r"\b([a-fA-F0-9]{64})\b", text)
if not m:
    raise SystemExit("Checksum file does not contain a valid SHA256.")
print(m.group(1).lower())
PY
)"
  local actual_sha
  actual_sha="$(sha256sum "${archive_file}" | awk '{print tolower($1)}')"
  if [[ "${expected_sha}" != "${actual_sha}" ]]; then
    err "Checksum mismatch."
    err "Expected: ${expected_sha}"
    err "Actual:   ${actual_sha}"
    exit 1
  fi
  log "Checksum verified."
}

install_release_payload() {
  local extract_dir="$1"
  log "Installing to ${INSTALL_DIR}"
  ${SUDO} rm -rf "${INSTALL_DIR}"
  ${SUDO} mkdir -p "${INSTALL_DIR}"
  ${SUDO} cp -a "${extract_dir}/." "${INSTALL_DIR}/"
  ${SUDO} chmod +x "${INSTALL_DIR}/${APP_BIN_NAME}"
}

write_installed_metadata() {
  local version="$1"
  local channel="$2"
  local metadata_tmp
  metadata_tmp="$(mktemp)"
  cat > "${metadata_tmp}" <<EOF
{
  "version": "${version}",
  "channel": "${channel}"
}
EOF
  ${SUDO} install -m 0644 "${metadata_tmp}" "${INSTALL_DIR}/version.json"
  rm -f "${metadata_tmp}"
}

restore_backup() {
  if [[ ! -d "${BACKUP_DIR}" ]]; then
    return
  fi
  log "Rolling back from backup..."
  ${SUDO} rm -rf "${INSTALL_DIR}"
  ${SUDO} mv "${BACKUP_DIR}" "${INSTALL_DIR}"
}

ROLLBACK_NEEDED="0"

on_error() {
  local exit_code=$?
  if [[ "${ROLLBACK_NEEDED}" == "1" ]]; then
    err "Install failed, starting rollback."
    restore_backup
  fi
  exit "${exit_code}"
}

main() {
  trap on_error ERR
  need_cmd curl
  need_cmd tar
  need_cmd sha256sum
  need_cmd mktemp
  need_cmd python3

  detect_os
  detect_arch

  if [[ -n "${SUDO}" ]] && ! command -v sudo >/dev/null 2>&1; then
    err "sudo is required when not running as root."
    exit 1
  fi

  local requested_channel=""
  local force_install="false"
  local update_mode="false"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --beta)
        requested_channel="beta"
        shift
        ;;
      --channel)
        if [[ $# -lt 2 ]]; then
          err "Missing value for --channel"
          exit 1
        fi
        requested_channel="$(normalize_channel "$2")"
        shift 2
        ;;
      --update)
        update_mode="true"
        shift
        ;;
      --force)
        force_install="true"
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        err "Unknown option: $1"
        usage
        exit 1
        ;;
    esac
  done

  mapfile -t LOCAL_META < <(read_local_metadata)
  LOCAL_VERSION="${LOCAL_META[0]:-}"
  LOCAL_CHANNEL_RAW="${LOCAL_META[1]:-stable}"
  LOCAL_CHANNEL="$(normalize_channel "${LOCAL_CHANNEL_RAW}")"

  if [[ -n "${requested_channel}" ]]; then
    TARGET_CHANNEL="$(normalize_channel "${requested_channel}")"
  elif [[ "${update_mode}" == "true" ]]; then
    TARGET_CHANNEL="${LOCAL_CHANNEL}"
  else
    TARGET_CHANNEL="stable"
  fi

  WORKDIR="$(mktemp -d)"
  trap 'rm -rf "${WORKDIR}"' EXIT
  RELEASE_JSON_FILE="${WORKDIR}/release.json"
  RELEASE_HEADERS_FILE="${WORKDIR}/release.headers"

  local extract_mode
  if [[ "${TARGET_CHANNEL}" == "stable" ]]; then
    log "Fetching latest stable release metadata"
    fetch_release_json "${LATEST_STABLE_API_URL}" "${RELEASE_HEADERS_FILE}" "${RELEASE_JSON_FILE}"
    extract_mode="stable_latest"
  elif [[ "${update_mode}" == "true" ]]; then
    log "Fetching release list for beta channel update"
    fetch_release_json "${ALL_RELEASES_API_URL}" "${RELEASE_HEADERS_FILE}" "${RELEASE_JSON_FILE}"
    extract_mode="beta_any"
  else
    log "Fetching latest prerelease metadata for beta channel"
    fetch_release_json "${ALL_RELEASES_API_URL}" "${RELEASE_HEADERS_FILE}" "${RELEASE_JSON_FILE}"
    extract_mode="beta_prerelease_only"
  fi

  mapfile -t META < <(extract_release_metadata "${extract_mode}")
  LATEST_VERSION="${META[0]}"
  ARCHIVE_URL="${META[1]}"
  CHECKSUM_URL="${META[2]}"
  LATEST_TAG="${META[3]}"
  IS_PRERELEASE="${META[4]}"

  if [[ "${TARGET_CHANNEL}" == "stable" && "${IS_PRERELEASE}" == "true" ]]; then
    err "Stable channel cannot install prerelease tags."
    exit 1
  fi

  log "Target channel: ${TARGET_CHANNEL}"
  log "Selected release: ${LATEST_VERSION} (${LATEST_TAG})"

  if [[ -n "${LOCAL_VERSION}" ]]; then
    log "Installed version: ${LOCAL_VERSION} (${LOCAL_CHANNEL})"
    if [[ "${force_install}" != "true" && "${LOCAL_VERSION}" == "${LATEST_VERSION}" && "${LOCAL_CHANNEL}" == "${TARGET_CHANNEL}" ]]; then
      echo "Fast Tools is already up to date"
      exit 0
    fi
  fi

  ARCHIVE_FILE="${WORKDIR}/release.tar.gz"
  CHECKSUM_FILE="${WORKDIR}/release.sha256"
  log "Downloading archive: ${ARCHIVE_URL}"
  curl -fsSL "${ARCHIVE_URL}" -o "${ARCHIVE_FILE}"
  verify_checksum "${ARCHIVE_FILE}" "${CHECKSUM_FILE}" "${CHECKSUM_URL}"

  EXTRACT_DIR="${WORKDIR}/extract"
  mkdir -p "${EXTRACT_DIR}"
  tar -xzf "${ARCHIVE_FILE}" -C "${EXTRACT_DIR}"

  if [[ -d "${INSTALL_DIR}" ]]; then
    log "Backing up current install to ${BACKUP_DIR}"
    ${SUDO} rm -rf "${BACKUP_DIR}"
    ${SUDO} mv "${INSTALL_DIR}" "${BACKUP_DIR}"
    ROLLBACK_NEEDED="1"
  fi

  install_release_payload "${EXTRACT_DIR}"
  write_installed_metadata "${LATEST_VERSION}" "${TARGET_CHANNEL}"

  log "Installing uninstall script"
  ${SUDO} curl -fsSL "${UNINSTALL_URL}" -o "${INSTALL_DIR}/uninstall.sh"
  ${SUDO} chmod +x "${INSTALL_DIR}/uninstall.sh"

  write_wrapper
  write_desktop_entry
  copy_icon_if_present

  if command -v update-desktop-database >/dev/null 2>&1; then
    ${SUDO} update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
  fi
  if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    ${SUDO} gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
  fi

  ROLLBACK_NEEDED="0"
  ${SUDO} rm -rf "${BACKUP_DIR}"
  log "Install complete."
  log "Run: fast-tools --version"
  log "Run: fast-tools --channel"
  log "Run: fast-tools --update"
}

main "$@"
