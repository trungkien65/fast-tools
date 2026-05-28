from __future__ import annotations

from PySide6.QtWidgets import QWidget

from app.core.package_checker import PackageStatus
from app.core.tools_config import Tool
from app.gui.component.tool_card import ToolCard


class ToolCardEntry:
    def __init__(self, tool: Tool, card: ToolCard, group: QWidget) -> None:
        self.tool = tool
        self.card = card
        self.group = group
        self.status = PackageStatus.NOT_INSTALLED
        self.installing = False
        self.uninstalling = False
        self.visible = True
