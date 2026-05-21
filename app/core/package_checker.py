from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence


PACKAGE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+.-]*$")


class PackageStatus(StrEnum):
    INSTALLED = "Installed"
    NOT_INSTALLED = "Not Installed"
    PACKAGE_NOT_FOUND = "Package Not Found"
    FAILED = "Failed"


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class PackageInfo:
    package: str
    installed: bool
    exists: bool
    version: str = ""
    command_available: bool | None = None
    status: PackageStatus = PackageStatus.NOT_INSTALLED


class PackageChecker:
    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds

    def check_status(self, package_name: str) -> PackageStatus:
        return self.check_package(package_name).status

    def check_package(self, package_name: str, command_name: str = "") -> PackageInfo:
        self._validate_package_name(package_name)
        installed, version = self.installed_version(package_name)
        exists = True if installed else self.package_exists(package_name)
        command_available = self.command_exists(command_name) if command_name else None

        if installed:
            status = PackageStatus.INSTALLED
        elif exists:
            status = PackageStatus.NOT_INSTALLED
        else:
            status = PackageStatus.PACKAGE_NOT_FOUND

        return PackageInfo(
            package=package_name,
            installed=installed,
            exists=exists,
            version=version,
            command_available=command_available,
            status=status,
        )

    def is_installed(self, package_name: str) -> bool:
        self._validate_package_name(package_name)
        result = self._run(
            ["dpkg-query", "-W", "-f=${Status}", package_name],
            timeout_seconds=self.timeout_seconds,
        )
        return result.returncode == 0 and "install ok installed" in result.stdout

    def installed_version(self, package_name: str) -> tuple[bool, str]:
        self._validate_package_name(package_name)
        result = self._run(
            ["dpkg-query", "-W", "-f=${Status}\t${Version}", package_name],
            timeout_seconds=self.timeout_seconds,
        )
        if result.returncode != 0 or "install ok installed" not in result.stdout:
            return False, ""

        parts = result.stdout.strip().split("\t", maxsplit=1)
        version = parts[1] if len(parts) == 2 else ""
        return True, version

    def package_exists(self, package_name: str) -> bool:
        self._validate_package_name(package_name)
        result = self._run(
            ["apt-cache", "show", package_name],
            timeout_seconds=self.timeout_seconds,
        )
        return result.returncode == 0 and bool(result.stdout.strip())

    @staticmethod
    def command_exists(command_name: str) -> bool:
        if not command_name or any(char in command_name for char in (" ", "/", "\\")):
            return False
        return shutil.which(command_name) is not None

    @staticmethod
    def _validate_package_name(package_name: str) -> None:
        if not PACKAGE_NAME_PATTERN.fullmatch(package_name):
            raise ValueError(f"Invalid package name: {package_name!r}")

    @staticmethod
    def _run(command: Sequence[str], timeout_seconds: int) -> CommandResult:
        try:
            completed = subprocess.run(
                list(command),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except FileNotFoundError as exc:
            return CommandResult(returncode=127, stderr=str(exc))
        except subprocess.TimeoutExpired as exc:
            return CommandResult(
                returncode=124,
                stdout=exc.stdout or "",
                stderr=exc.stderr or f"Command timed out after {timeout_seconds}s",
            )

        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
