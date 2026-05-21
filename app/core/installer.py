from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Sequence

from app.core.package_checker import PackageChecker


@dataclass(frozen=True)
class InstallResult:
    package: str
    success: bool
    message: str
    stdout: str = ""
    stderr: str = ""


class PackageInstaller:
    def __init__(
        self,
        checker: PackageChecker | None = None,
        timeout_seconds: int = 900,
        auth_command: str = "pkexec",
    ) -> None:
        self.checker = checker or PackageChecker()
        self.timeout_seconds = timeout_seconds
        self.auth_command = auth_command

    def install(self, package_name: str) -> InstallResult:
        self.checker._validate_package_name(package_name)
        if not self.checker.package_exists(package_name):
            return InstallResult(
                package=package_name,
                success=False,
                message=f"Package not found: {package_name}",
            )

        command = [self.auth_command, "apt", "install", "-y", package_name]
        result = self._run(command)
        if result.returncode == 127 and self.auth_command == "pkexec":
            result = self._run(["sudo", "apt", "install", "-y", package_name])

        if result.returncode == 0:
            return InstallResult(
                package=package_name,
                success=True,
                message=f"Installed {package_name}",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        output = result.stderr.strip() or result.stdout.strip() or "Unknown install error"
        return InstallResult(
            package=package_name,
            success=False,
            message=f"Failed to install {package_name}: {output}",
            stdout=result.stdout,
            stderr=result.stderr,
        )

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
                stderr=exc.stderr or f"Install timed out after {self.timeout_seconds}s",
            )
