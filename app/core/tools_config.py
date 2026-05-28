from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TOOLS_PATH = Path(__file__).resolve().parents[1] / "config" / "tools.json"
JETBRAINS_TOOLBOX_PACKAGE = "jetbrains-toolbox"
JETBRAINS_TOOLBOX_PACKAGE_PREFIX = "jetbrains-toolbox-"
JETBRAINS_TOOLBOX_APPS_PATH = Path.home() / ".local/share/JetBrains/Toolbox/apps"
JETBRAINS_IDE_NAMES = {
    "androidstudio": "Android Studio",
    "aqua": "Aqua",
    "clion": "CLion",
    "datagrip": "DataGrip",
    "dataspell": "DataSpell",
    "goland": "GoLand",
    "fleet": "JetBrains Fleet",
    "gateway": "JetBrains Gateway",
    "idea": "IntelliJ IDEA",
    "mps": "MPS",
    "phpstorm": "PhpStorm",
    "pycharm": "PyCharm",
    "rider": "Rider",
    "rubymine": "RubyMine",
    "rustrover": "RustRover",
    "webstorm": "WebStorm",
    "writerside": "Writerside",
}


@dataclass(frozen=True)
class Tool:
    name: str
    package: str
    service: str = ""
    category: str = "general"
    command: str = ""
    description: str = ""
    install_method: str = "apt"
    install_command: str = ""
    uninstall_command: str = ""
    deb_url: str = ""
    uninstall_package: str = ""


def load_tools(config_path: Path | str = DEFAULT_TOOLS_PATH) -> list[Tool]:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as config_file:
        raw_config: dict[str, Any] = json.load(config_file)

    tools = raw_config.get("tools")
    if not isinstance(tools, list):
        raise ValueError("tools.json must contain a 'tools' list")

    parsed_tools: list[Tool] = []
    for index, item in enumerate(tools):
        if not isinstance(item, dict):
            raise ValueError(f"Tool entry {index} must be an object")

        name = item.get("name")
        package = item.get("package")
        service = item.get("service", "")
        category = item.get("category", "general")
        command = item.get("command", "")
        description = item.get("description", "")
        install_method = item.get("install_method", "apt")
        install_command = item.get("install_command", "")
        uninstall_command = item.get("uninstall_command", "")
        deb_url = item.get("deb_url", "")
        uninstall_package = item.get("uninstall_package", "")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Tool entry {index} is missing a valid name")
        if not isinstance(package, str) or not package:
            raise ValueError(f"Tool entry {index} is missing a valid package")
        if not isinstance(description, str):
            raise ValueError(f"Tool entry {index} has an invalid description")
        if not isinstance(service, str):
            raise ValueError(f"Tool entry {index} has an invalid service")
        if not isinstance(category, str) or not category:
            raise ValueError(f"Tool entry {index} has an invalid category")
        if not isinstance(command, str):
            raise ValueError(f"Tool entry {index} has an invalid command")
        if install_method not in {"apt", "deb_url", "command"}:
            raise ValueError(f"Tool entry {index} has an invalid install_method")
        if not isinstance(install_command, str):
            raise ValueError(f"Tool entry {index} has an invalid install_command")
        if not isinstance(uninstall_command, str):
            raise ValueError(f"Tool entry {index} has an invalid uninstall_command")
        if not isinstance(deb_url, str):
            raise ValueError(f"Tool entry {index} has an invalid deb_url")
        if not isinstance(uninstall_package, str):
            raise ValueError(f"Tool entry {index} has an invalid uninstall_package")

        if package == JETBRAINS_TOOLBOX_PACKAGE:
            continue

        parsed_tools.append(
            Tool(
                name=name,
                package=package,
                service=service,
                category=category,
                command=command,
                description=description,
                install_method=install_method,
                install_command=install_command,
                uninstall_command=uninstall_command,
                deb_url=deb_url,
                uninstall_package=uninstall_package,
            )
        )

    if path == DEFAULT_TOOLS_PATH:
        return merge_tools(parsed_tools, load_jetbrains_toolbox_tools())
    return parsed_tools


def merge_tools(primary: list[Tool], additional: list[Tool]) -> list[Tool]:
    packages = {tool.package for tool in primary}
    merged = list(primary)
    for tool in additional:
        if tool.package in packages:
            continue
        packages.add(tool.package)
        merged.append(tool)
    return merged


def load_jetbrains_toolbox_tools(
    apps_path: Path = JETBRAINS_TOOLBOX_APPS_PATH,
) -> list[Tool]:
    if not apps_path.is_dir():
        return []

    tools: list[Tool] = []
    for app_path in sorted(apps_path.iterdir(), key=lambda path: path.name.lower()):
        if not app_path.is_dir():
            continue

        slug = app_path.name.lower()
        executable = app_path / "bin" / slug
        launcher = app_path / "bin" / f"{slug}.sh"
        if not executable.exists() and not launcher.exists():
            continue

        tools.append(
            Tool(
                name=JETBRAINS_IDE_NAMES.get(slug, slug.replace("-", " ").title()),
                package=f"{JETBRAINS_TOOLBOX_PACKAGE_PREFIX}{slug}",
                service="",
                category="jetbrains",
                command=slug,
                description="JetBrains IDE installed by JetBrains Toolbox",
            )
        )

    return tools
