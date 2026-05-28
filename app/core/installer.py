from __future__ import annotations

import os
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Sequence

from app.core.package_checker import PackageChecker
from app.core.tools_config import Tool


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

    def install_tool(self, tool: Tool) -> InstallResult:
        if tool.install_method == "apt":
            return self.install(tool.package)
        if tool.install_method == "deb_url":
            return self.install_from_deb_url(tool)
        if tool.install_method == "command":
            if not tool.install_command.strip():
                return InstallResult(
                    package=tool.package,
                    success=False,
                    message=f"Install command is not configured for {tool.name}",
                )
            return self._run_custom_command(tool, tool.install_command, action="install")
        return InstallResult(
            package=tool.package,
            success=False,
            message=f"Unsupported install method: {tool.install_method}",
        )

    def uninstall(self, package_name: str) -> InstallResult:
        self.checker._validate_package_name(package_name)
        if not self.checker.is_installed(package_name):
            return InstallResult(
                package=package_name,
                success=False,
                message=f"Package is not installed: {package_name}",
            )

        command = [self.auth_command, "apt", "remove", "-y", package_name]
        result = self._run(command)
        if result.returncode == 127 and self.auth_command == "pkexec":
            result = self._run(["sudo", "apt", "remove", "-y", package_name])

        if result.returncode == 0:
            return InstallResult(
                package=package_name,
                success=True,
                message=f"Uninstalled {package_name}",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        output = result.stderr.strip() or result.stdout.strip() or "Unknown uninstall error"
        return InstallResult(
            package=package_name,
            success=False,
            message=f"Failed to uninstall {package_name}: {output}",
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def uninstall_tool(self, tool: Tool) -> InstallResult:
        if tool.install_method == "apt":
            return self.uninstall(tool.package)
        if tool.install_method == "deb_url":
            package_name = tool.uninstall_package.strip() or tool.package
            return self.uninstall(package_name)
        if tool.install_method == "command":
            if not tool.uninstall_command.strip():
                return InstallResult(
                    package=tool.package,
                    success=False,
                    message=f"Uninstall command is not configured for {tool.name}",
                )
            return self._run_custom_command(tool, tool.uninstall_command, action="uninstall")
        return InstallResult(
            package=tool.package,
            success=False,
            message=f"Unsupported install method: {tool.install_method}",
        )

    def install_from_deb_url(self, tool: Tool) -> InstallResult:
        deb_url = tool.deb_url.strip()
        if not deb_url:
            return InstallResult(
                package=tool.package,
                success=False,
                message=f"deb_url is not configured for {tool.name}",
            )

        with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as temp_file:
            deb_path = temp_file.name

        try:
            urllib.request.urlretrieve(deb_url, deb_path)
            result = self._run_auth_apt_install_target(deb_path)
            if result.returncode == 0:
                return InstallResult(
                    package=tool.package,
                    success=True,
                    message=f"Installed {tool.name} from {deb_url}",
                    stdout=result.stdout,
                    stderr=result.stderr,
                )

            output = result.stderr.strip() or result.stdout.strip() or "Unknown install error"
            return InstallResult(
                package=tool.package,
                success=False,
                message=f"Failed to install {tool.name} from deb_url: {output}",
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except Exception as exc:
            return InstallResult(
                package=tool.package,
                success=False,
                message=f"Failed to download deb for {tool.name}: {exc}",
            )
        finally:
            try:
                os.remove(deb_path)
            except OSError:
                pass

    def _run_auth_apt_install_target(self, target: str) -> subprocess.CompletedProcess[str]:
        result = self._run([self.auth_command, "apt", "install", "-y", target])
        if result.returncode == 127 and self.auth_command == "pkexec":
            return self._run(["sudo", "apt", "install", "-y", target])
        return result

    def _run_custom_command(self, tool: Tool, command_text: str, action: str) -> InstallResult:
        result = self._run(["bash", "-lc", command_text])
        if result.returncode == 0:
            return InstallResult(
                package=tool.package,
                success=True,
                message=f"{action.capitalize()}ed {tool.name}",
                stdout=result.stdout,
                stderr=result.stderr,
            )

        output = result.stderr.strip() or result.stdout.strip() or f"Unknown {action} error"
        return InstallResult(
            package=tool.package,
            success=False,
            message=f"Failed to {action} {tool.name}: {output}",
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
