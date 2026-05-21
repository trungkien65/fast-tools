from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence


SERVICE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_.@:-]+$")


class ServiceState(StrEnum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    NOT_FOUND = "Not Found"
    UNKNOWN = "Unknown"


@dataclass(frozen=True)
class ServiceInfo:
    name: str
    exists: bool
    active_state: ServiceState = ServiceState.UNKNOWN
    enabled: bool | None = None


class ServiceManager:
    def __init__(self, timeout_seconds: int = 10, auth_command: str = "pkexec") -> None:
        self.timeout_seconds = timeout_seconds
        self.auth_command = auth_command

    def inspect(self, service_name: str) -> ServiceInfo:
        self._validate_service_name(service_name)

        active_result = self._run(["systemctl", "is-active", service_name])
        enabled_result = self._run(["systemctl", "is-enabled", service_name])

        active_text = active_result.stdout.strip()
        enabled_text = enabled_result.stdout.strip()
        not_found = (
            "could not be found" in active_result.stderr.lower()
            or "not-found" in active_text
            or "not-found" in enabled_text
        )
        if not_found:
            return ServiceInfo(name=service_name, exists=False, active_state=ServiceState.NOT_FOUND)

        if active_text == "active":
            active_state = ServiceState.ACTIVE
        elif active_text in {"inactive", "failed", "activating", "deactivating"}:
            active_state = ServiceState.INACTIVE
        else:
            active_state = ServiceState.UNKNOWN

        enabled = enabled_text == "enabled" if enabled_result.returncode == 0 else False
        return ServiceInfo(
            name=service_name,
            exists=active_result.returncode in {0, 3} or enabled_result.returncode == 0,
            active_state=active_state,
            enabled=enabled,
        )

    def start(self, service_name: str) -> subprocess.CompletedProcess[str]:
        return self._control("start", service_name)

    def stop(self, service_name: str) -> subprocess.CompletedProcess[str]:
        return self._control("stop", service_name)

    def restart(self, service_name: str) -> subprocess.CompletedProcess[str]:
        return self._control("restart", service_name)

    def enable(self, service_name: str) -> subprocess.CompletedProcess[str]:
        return self._control("enable", service_name)

    def disable(self, service_name: str) -> subprocess.CompletedProcess[str]:
        return self._control("disable", service_name)

    def _control(self, action: str, service_name: str) -> subprocess.CompletedProcess[str]:
        self._validate_service_name(service_name)
        if action not in {"start", "stop", "restart", "enable", "disable"}:
            raise ValueError(f"Invalid service action: {action}")
        return self._run([self.auth_command, "systemctl", action, service_name])

    @staticmethod
    def _validate_service_name(service_name: str) -> None:
        if not SERVICE_NAME_PATTERN.fullmatch(service_name):
            raise ValueError(f"Invalid service name: {service_name!r}")

    def _run(self, command: Sequence[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                list(command),
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            return subprocess.CompletedProcess(
                args=list(command),
                returncode=127,
                stdout="",
                stderr=str(exc),
            )
        except subprocess.TimeoutExpired as exc:
            return subprocess.CompletedProcess(
                args=list(command),
                returncode=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or f"Command timed out after {self.timeout_seconds}s",
            )
