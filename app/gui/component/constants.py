from __future__ import annotations

from app.core.tools_config import Tool


CARD_MIN_WIDTH = 200
CARD_MAX_WIDTH = 320

GROUP_ORDER = {
    "recommend": 0,
    "tool": 1,
    "database": 2,
    "language": 3,
    "runtime": 4,
    "ide": 5,
    "jetbrains": 6,
    "code": 7,
    "office": 8,
    "network": 9,
    "web": 10,
    "container": 11,
    "system": 12,
}
GROUP_LABELS = {
    "recommend": "Recommended",
    "tool": "Tools",
    "database": "Database",
    "language": "Programming Languages",
    "runtime": "Runtime & Package Managers",
    "ide": "IDE",
    "jetbrains": "JetBrains Toolbox",
    "code": "Code",
    "office": "Office",
    "network": "Network",
    "web": "Web",
    "container": "Container",
    "system": "System",
}


def group_label(category: str) -> str:
    return GROUP_LABELS.get(category, category.replace("-", " ").title())


def sorted_categories(tools: list[Tool]) -> list[str]:
    return sorted(
        {tool.category for tool in tools},
        key=lambda category: (GROUP_ORDER.get(category, 100), group_label(category)),
    )
