from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QGridLayout, QPushButton, QWidget

from app.gui.component.tool_card_entry import ToolCardEntry


class ToolGroup:
    def __init__(
        self,
        widget: QWidget,
        grid: QGridLayout,
        select_all_checkbox: QCheckBox,
        toolbox_button: QPushButton | None = None,
    ) -> None:
        self.widget = widget
        self.grid = grid
        self.select_all_checkbox = select_all_checkbox
        self.toolbox_button = toolbox_button
        self.entries: list[ToolCardEntry] = []
