from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QWidget

from app.gui.component.tool_card_entry import ToolCardEntry


class ToolGroup:
    def __init__(self, widget: QWidget, grid: QGridLayout) -> None:
        self.widget = widget
        self.grid = grid
        self.entries: list[ToolCardEntry] = []
