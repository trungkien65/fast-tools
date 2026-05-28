#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist-release"
PACKAGE_JSON="${ROOT_DIR}/package.json"
VERSION_JSON="${ROOT_DIR}/version.json"

AMD64_BIN="${AMD64_BIN:-${ROOT_DIR}/artifacts/linux-amd64/fast-tools}"
ARM64_BIN="${ARM64_BIN:-${ROOT_DIR}/artifacts/linux-arm64/fast-tools}"
ICON_PATH="${ICON_PATH:-${ROOT_DIR}/artifacts/common/icon.png}"
BUILD_CMD="${BUILD_CMD:-}"
TARGET_ARCHES="${TARGET_ARCHES:-amd64,arm64}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

read_version() {
  python3 - "${PACKAGE_JSON}" <<'PY'
import json
import sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    version = str(json.load(f).get("version", "")).strip()
if not version:
    raise SystemExit("package.json does not contain a valid version.")
print(version)
PY
}

make_version_json() {
  local out_file="$1"
  local version="$2"
  cat > "${out_file}" <<EOF
{
  "version": "${version}"
}
EOF
}

pack_arch() {
  local arch="$1"
  local bin_path="$2"
  local version="$3"

  if [[ ! -f "${bin_path}" ]]; then
    echo "Missing binary for ${arch}: ${bin_path}" >&2
    exit 1
  fi

  local stage_dir
  stage_dir="$(mktemp -d)"

  cp -f "${bin_path}" "${stage_dir}/fast-tools"
  chmod +x "${stage_dir}/fast-tools"
  make_version_json "${stage_dir}/version.json" "${version}"
  if [[ -f "${ICON_PATH}" ]]; then
    cp -f "${ICON_PATH}" "${stage_dir}/icon.png"
  fi

  local name="fast-tools-linux-${arch}-v${version}.tar.gz"
  local out="${DIST_DIR}/${name}"
  tar -czf "${out}" -C "${stage_dir}" .
  sha256sum "${out}" | awk '{print $1}' > "${out}.sha256"
  rm -rf "${stage_dir}"
}

arch_enabled() {
  local target="$1"
  python3 - "${TARGET_ARCHES}" "${target}" <<'PY'
import sys
targets = {x.strip() for x in sys.argv[1].split(",") if x.strip()}
print("yes" if sys.argv[2] in targets else "no")
PY
}

main() {
  need_cmd python3
  need_cmd tar
  need_cmd sha256sum

  local version
  version="$(read_version)"
  echo "Building release for version ${version}"

  if [[ ! -f "${PACKAGE_JSON}" ]]; then
    echo "Missing package.json at ${PACKAGE_JSON}" >&2
    exit 1
  fi

  if [[ -n "${BUILD_CMD}" ]]; then
    echo "Running build command: ${BUILD_CMD}"
    # shellcheck disable=SC2086
    eval ${BUILD_CMD}
  fi

  rm -rf "${DIST_DIR}"
  mkdir -p "${DIST_DIR}"

  cat > "${VERSION_JSON}" <<EOF
{
  "version": "${version}"
}
EOF

  cp -f "${ROOT_DIR}/install.sh" "${DIST_DIR}/install.sh"
  cp -f "${ROOT_DIR}/uninstall.sh" "${DIST_DIR}/uninstall.sh"
  chmod +x "${DIST_DIR}/install.sh" "${DIST_DIR}/uninstall.sh"

  if [[ "$(arch_enabled "amd64")" == "yes" ]]; then
    pack_arch "amd64" "${AMD64_BIN}" "${version}"
  fi
  if [[ "$(arch_enabled "arm64")" == "yes" ]]; then
    pack_arch "arm64" "${ARM64_BIN}" "${version}"
  fi

  echo "Release artifacts generated at ${DIST_DIR}"
}

main "$@"
