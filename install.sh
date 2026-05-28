#!/usr/bin/env bash
set -euo pipefail

GITHUB_OWNER="trungkien65"
GITHUB_REPO="fast-tools"
APP_NAME="fast-tools"
APP_BIN_NAME="fast-tools"
INSTALL_DIR="/opt/fast-tools"
BIN_LINK="/usr/local/bin/fast-tools"
DESKTOP_FILE="/usr/share/applications/fast-tools.desktop"
ICON_DEST_HICOLOR="/usr/share/icons/hicolor/256x256/apps/fast-tools.png"
BACKUP_DIR="/opt/fast-tools.backup"
INSTALL_REF="${FAST_TOOLS_INSTALL_REF:-main}"
RAW_BASE_URL="https://raw.githubusercontent.com/${GITHUB_OWNER}/${GITHUB_REPO}/${INSTALL_REF}"
LATEST_API_URL="https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest"
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

version_lt() {
  local left="$1"
  local right="$2"
  dpkg --compare-versions "${left}" lt "${right}"
}

version_eq() {
  local left="$1"
  local right="$2"
  dpkg --compare-versions "${left}" eq "${right}"
}

read_local_version() {
  local version_file="${INSTALL_DIR}/version.json"
  if [[ ! -f "${version_file}" ]]; then
    echo ""
    return
  fi

  python3 - "${version_file}" <<'PY'
import json
import sys
path = sys.argv[1]
try:
    with open(path, "r", encoding="utf-8") as f:
        print(json.load(f).get("version", ""))
except Exception:
    print("")
PY
}

extract_release_metadata() {
  python3 - "${RELEASE_JSON_FILE}" "${ARCH}" <<'PY'
import json
import sys
path, arch = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
tag_name = str(data.get("tag_name", "")).strip()
if not tag_name:
    raise SystemExit("Release tag is missing from GitHub API response")
version = tag_name[1:] if tag_name.startswith("v") else tag_name
target = f"fast-tools-linux-{arch}-v{version}.tar.gz"
sha_target = f"{target}.sha256"
assets = data.get("assets", [])
archive_url = ""
checksum_url = ""
for asset in assets:
    name = asset.get("name", "")
    if name == target:
        archive_url = asset.get("browser_download_url", "")
    if name == sha_target:
        checksum_url = asset.get("browser_download_url", "")
if not archive_url:
    raise SystemExit(f"Release asset not found: {target}")
print(version)
print(archive_url)
print(checksum_url)
print(tag_name)
PY
}

write_wrapper_template() {
  local wrapper_file
  wrapper_file="$(mktemp)"

  cat > "${wrapper_file}" <<EOF
#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR}"
INSTALL_SCRIPT_URL="${INSTALL_SCRIPT_URL}"
APP_BIN="\${INSTALL_DIR}/${APP_BIN_NAME}"
VERSION_FILE="\${INSTALL_DIR}/version.json"
UNINSTALL_SCRIPT="\${INSTALL_DIR}/uninstall.sh"

print_version() {
  if [[ ! -f "\${VERSION_FILE}" ]]; then
    echo "unknown"
    return
  fi
  python3 - "\${VERSION_FILE}" <<'PY'
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

if [[ "\${1:-}" == "--version" ]]; then
  print_version
  exit 0
fi

if [[ "\${1:-}" == "--update" ]]; then
  exec bash -c "curl -fsSL \${INSTALL_SCRIPT_URL} | bash"
fi

if [[ "\${1:-}" == "--uninstall" ]]; then
  if [[ -x "\${UNINSTALL_SCRIPT}" ]]; then
    exec "\${UNINSTALL_SCRIPT}"
  fi
  echo "Uninstall script not found at \${UNINSTALL_SCRIPT}"
  exit 1
fi

if [[ ! -x "\${APP_BIN}" ]]; then
  echo "Fast Tools binary not found at \${APP_BIN}"
  exit 1
fi

exec "\${APP_BIN}" "\$@"
EOF

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

fetch_latest_release_json() {
  local headers_file="$1"
  local body_file="$2"

  if ! curl -sS -D "${headers_file}" -o "${body_file}" "${LATEST_API_URL}"; then
    err "Failed to call GitHub Releases API."
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

verify_checksum_if_available() {
  local archive_file="$1"
  local checksum_file="$2"
  local checksum_url="$3"

  if [[ -z "${checksum_url}" ]]; then
    log "Checksum asset not found. Skipping SHA256 verification."
    return
  fi

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
  need_cmd dpkg

  detect_os
  detect_arch

  if [[ -n "${SUDO}" ]] && ! command -v sudo >/dev/null 2>&1; then
    err "sudo is required when not running as root."
    exit 1
  fi

  WORKDIR="$(mktemp -d)"
  trap 'rm -rf "${WORKDIR}"' EXIT
  RELEASE_JSON_FILE="${WORKDIR}/release.json"
  RELEASE_HEADERS_FILE="${WORKDIR}/release.headers"

  log "Fetching latest release from GitHub API"
  fetch_latest_release_json "${RELEASE_HEADERS_FILE}" "${RELEASE_JSON_FILE}"

  mapfile -t META < <(extract_release_metadata)
  LATEST_VERSION="${META[0]}"
  ARCHIVE_URL="${META[1]}"
  CHECKSUM_URL="${META[2]}"
  LATEST_TAG="${META[3]}"

  log "Latest version: ${LATEST_VERSION} (${LATEST_TAG})"
  LOCAL_VERSION="$(read_local_version || true)"
  if [[ -n "${LOCAL_VERSION}" ]]; then
    log "Installed version: ${LOCAL_VERSION}"
    if version_eq "${LOCAL_VERSION}" "${LATEST_VERSION}"; then
      echo "Fast Tools is already up to date"
      exit 0
    fi
  fi

  ARCHIVE_FILE="${WORKDIR}/release.tar.gz"
  CHECKSUM_FILE="${WORKDIR}/release.sha256"
  log "Downloading archive: ${ARCHIVE_URL}"
  curl -fsSL "${ARCHIVE_URL}" -o "${ARCHIVE_FILE}"
  verify_checksum_if_available "${ARCHIVE_FILE}" "${CHECKSUM_FILE}" "${CHECKSUM_URL}"

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
  log "Run: fast-tools --update"
}

main "$@"
