from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_TOOLS_PATH = Path(__file__).resolve().parents[1] / "config" / "tools.json"


@dataclass(frozen=True)
class Tool:
    name: str
    package: str
    service: str = ""
    category: str = "general"
    command: str = ""
    description: str = ""


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

        parsed_tools.append(
            Tool(
                name=name,
                package=package,
                service=service,
                category=category,
                command=command,
                description=description,
            )
        )

    return parsed_tools
