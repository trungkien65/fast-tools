from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLineEdit, QWidget

from app.core.tools_config import Tool
from app.gui.component.constants import group_label, sorted_categories


class FilterBar(QWidget):
    filters_changed = Signal()

    def __init__(self, tools: list[Tool]) -> None:
        super().__init__()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search name or package")
        self.search_input.textChanged.connect(self.filters_changed)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All groups")
        for category in sorted_categories(tools):
            self.category_filter.addItem(group_label(category), category)
        self.category_filter.currentTextChanged.connect(self.filters_changed)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.search_input)
        layout.addWidget(self.category_filter)
        self.setLayout(layout)

    @property
    def search_text(self) -> str:
        return self.search_input.text().strip().lower()

    @property
    def selected_category(self) -> str | None:
        return self.category_filter.currentData()

    def set_controls_enabled(self, enabled: bool) -> None:
        self.search_input.setEnabled(enabled)
        self.category_filter.setEnabled(enabled)
