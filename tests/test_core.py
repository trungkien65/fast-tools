import json
import subprocess

import pytest

from app.core.installer import PackageInstaller
from app.core.package_checker import CommandResult, PackageChecker, PackageStatus
from app.core.service_manager import ServiceManager
from app.core.tools_config import load_tools


class FakeChecker(PackageChecker):
    def __init__(self, installed: set[str] | None = None, existing: set[str] | None = None) -> None:
        self.installed = installed or set()
        self.existing = existing or set()

    def is_installed(self, package_name: str) -> bool:
        self._validate_package_name(package_name)
        return package_name in self.installed

    def installed_version(self, package_name: str) -> tuple[bool, str]:
        self._validate_package_name(package_name)
        return package_name in self.installed, "1.0" if package_name in self.installed else ""

    def package_exists(self, package_name: str) -> bool:
        self._validate_package_name(package_name)
        return package_name in self.existing


def test_load_tools_reads_json_config(tmp_path):
    config = tmp_path / "tools.json"
    config.write_text(
        json.dumps({"tools": [{"name": "Git", "package": "git", "description": "VCS"}]}),
        encoding="utf-8",
    )

    tools = load_tools(config)

    assert len(tools) == 1
    assert tools[0].name == "Git"
    assert tools[0].package == "git"
    assert tools[0].category == "general"


def test_load_tools_reads_extended_metadata(tmp_path):
    config = tmp_path / "tools.json"
    config.write_text(
        json.dumps(
            {
                "tools": [
                    {
                        "name": "Redis",
                        "package": "redis-server",
                        "service": "redis-server",
                        "category": "database",
                        "command": "redis-server",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    tool = load_tools(config)[0]

    assert tool.service == "redis-server"
    assert tool.category == "database"
    assert tool.command == "redis-server"


def test_check_status_distinguishes_installed_available_and_missing():
    assert FakeChecker(installed={"git"}).check_status("git") == PackageStatus.INSTALLED
    assert FakeChecker(existing={"nginx"}).check_status("nginx") == PackageStatus.NOT_INSTALLED
    assert FakeChecker().check_status("missing") == PackageStatus.PACKAGE_NOT_FOUND


def test_check_package_returns_structured_result():
    result = FakeChecker(installed={"git"}).check_package("git")

    assert result.installed is True
    assert result.exists is True
    assert result.version == "1.0"
    assert result.status == PackageStatus.INSTALLED


def test_package_name_validation_rejects_shell_strings():
    with pytest.raises(ValueError):
        PackageChecker._validate_package_name("git; rm -rf /")


def test_installer_rejects_missing_package():
    installer = PackageInstaller(checker=FakeChecker(existing=set()))

    result = installer.install("missing")

    assert result.success is False
    assert result.message == "Package not found: missing"


def test_installer_uses_argument_array(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    installer = PackageInstaller(checker=FakeChecker(existing={"git"}))

    result = installer.install("git")

    assert result.success is True
    assert calls[0][0] == ["pkexec", "apt", "install", "-y", "git"]
    assert calls[0][1]["shell"] is not True if "shell" in calls[0][1] else True


def test_run_handles_missing_command(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("missing")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = PackageChecker._run(["dpkg-query"], timeout_seconds=1)

    assert result == CommandResult(returncode=127, stderr="missing")


def test_service_name_validation_rejects_shell_strings():
    with pytest.raises(ValueError):
        ServiceManager._validate_service_name("nginx; reboot")
