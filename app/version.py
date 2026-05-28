from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

APP_NAME = "Fast Tools"
DEFAULT_VERSION = "0.0.0"


@lru_cache(maxsize=1)
def get_app_version() -> str:
    version_file_candidates = [
        Path("/opt/fast-tools/version.json"),
        Path(__file__).resolve().parents[1] / "version.json",
        Path(__file__).resolve().parents[2] / "version.json",
    ]

    for version_file in version_file_candidates:
        if not version_file.exists():
            continue
        try:
            payload = json.loads(version_file.read_text(encoding="utf-8"))
            version = str(payload.get("version", "")).strip()
            if version:
                return version
        except (OSError, json.JSONDecodeError):
            continue

    return DEFAULT_VERSION
