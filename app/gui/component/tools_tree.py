from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.package_checker import PackageInfo, PackageStatus
from app.core.tools_config import Tool
from app.gui.component.constants import CARD_MIN_WIDTH, group_label, sorted_categories
from app.gui.component.tool_card import ToolCard
from app.gui.component.tool_card_entry import ToolCardEntry
from app.gui.component.tool_group import ToolGroup


class ToolsTree(QWidget):
    JETBRAINS_TOOLTIP = "Install or remove this IDE from JetBrains Toolbox"
    toolbox_requested = Signal()

    def __init__(self, tools: list[Tool]) -> None:
        super().__init__()
        self.tools = tools
        self.tool_items: list[ToolCardEntry] = []
        self.groups: dict[str, ToolGroup] = {}
        self._reflow_pending = False

        self.content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(12)
        self.content.setLayout(self.content_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setWidget(self.content)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)

        self.populate()

    def populate(self) -> None:
        self.tool_items = []
        self.groups = {}

        for category in sorted_categories(self.tools):
            category_tools = sorted(
                [tool for tool in self.tools if tool.category == category],
                key=lambda tool: tool.name.lower(),
            )

            group = QWidget()
            group_layout = QVBoxLayout()
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(6)

            group_header = QHBoxLayout()
            group_header.setContentsMargins(0, 0, 0, 0)
            group_header.setSpacing(8)

            group_label_widget = QLabel(f"{group_label(category)} ({len(category_tools)})")
            group_label_widget.setObjectName("toolGroupLabel")
            group_header.addWidget(group_label_widget)

            if category == "jetbrains":
                open_toolbox_button = QPushButton("Open Toolbox")
                open_toolbox_button.setCursor(Qt.CursorShape.PointingHandCursor)
                open_toolbox_button.clicked.connect(self.toolbox_requested.emit)
                group_header.addWidget(open_toolbox_button, 0, Qt.AlignmentFlag.AlignLeft)

            group_header.addStretch()
            group_layout.addLayout(group_header)

            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(18)
            grid.setVerticalSpacing(8)
            group_layout.addLayout(grid)

            tool_group = ToolGroup(widget=group, grid=grid)

            for tool in category_tools:
                card = ToolCard(tool.name, description=tool.description)
                card.setToolTip(tool.description or tool.package)
                if tool.category == "jetbrains":
                    card.set_checkbox_enabled(False)
                    card.setToolTip(self.JETBRAINS_TOOLTIP)
                entry = ToolCardEntry(tool=tool, card=card, group=group)
                self.tool_items.append(entry)
                tool_group.entries.append(entry)

            group.setLayout(group_layout)
            self.groups[category] = tool_group
            self.content_layout.addWidget(group)

        self.content_layout.addStretch()
        self.schedule_reflow()
        self.setStyleSheet(
            """
            QLabel#toolGroupLabel {
                font-weight: 700;
                margin-top: 8px;
            }
            """
        )

    def apply_filters(self, search: str, category: str | None) -> None:
        for item in self.tool_items:
            matches_search = (
                not search
                or search in item.tool.name.lower()
                or search in item.tool.package.lower()
            )
            matches_category = category is None or category == item.tool.category
            item.visible = matches_search and matches_category

        self.schedule_reflow()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.schedule_reflow()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.schedule_reflow()

    def schedule_reflow(self) -> None:
        if self._reflow_pending:
            return
        self._reflow_pending = True
        QTimer.singleShot(0, self.reflow_cards)

    def reflow_cards(self) -> None:
        self._reflow_pending = False
        viewport_width = max(
            self.scroll_area.viewport().width(),
            self.scroll_area.width(),
            self.width(),
            CARD_MIN_WIDTH,
        )

        for group in self.groups.values():
            gap = max(group.grid.horizontalSpacing(), 0)
            columns = max(1, (viewport_width + gap) // (CARD_MIN_WIDTH + gap))

            while group.grid.count():
                layout_item = group.grid.takeAt(0)
                if layout_item.widget():
                    layout_item.widget().setParent(None)

            for column in range(max(columns, group.grid.columnCount())):
                group.grid.setColumnStretch(column, 0)

            visible_entries = [entry for entry in group.entries if entry.visible]
            for entry in group.entries:
                if not entry.visible:
                    entry.card.setVisible(False)
            for index, entry in enumerate(visible_entries):
                row = index // columns
                column = index % columns
                group.grid.addWidget(
                    entry.card,
                    row,
                    column,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                )
                entry.card.setVisible(True)

            for column in range(columns):
                group.grid.setColumnStretch(column, 1)
            group.widget.setVisible(bool(visible_entries))

    def package_for_item(self, item: ToolCardEntry) -> str:
        return item.tool.package

    def command_for_item(self, item: ToolCardEntry) -> str:
        return item.tool.command

    def service_for_item(self, item: ToolCardEntry) -> str:
        return item.tool.service

    def card_for_item(self, item: ToolCardEntry) -> ToolCard:
        return item.card

    def update_package_status(
        self,
        item: ToolCardEntry,
        status: PackageStatus,
        package_info: PackageInfo | None,
    ) -> None:
        version = package_info.version if package_info else ""
        item.status = status
        item.installing = False
        item.uninstalling = False
        item.card.set_version_hint(version if version else status.value)
        item.card.set_checked(status == PackageStatus.INSTALLED)

        if status == PackageStatus.INSTALLED:
            item.card.setToolTip("Uncheck to uninstall")
        elif status == PackageStatus.PACKAGE_NOT_FOUND:
            item.card.setToolTip("Package was not found by apt-cache")
        else:
            item.card.setToolTip("Select to install")

        if item.tool.category == "jetbrains":
            item.card.setToolTip(self.JETBRAINS_TOOLTIP)

    def update_service_status(self, item: ToolCardEntry, _service_info: object | None) -> None:
        return

    def selected_installable_items(self) -> list[ToolCardEntry]:
        items: list[ToolCardEntry] = []
        for item in self.tool_items:
            if (
                item.card.is_checked()
                and item.status == PackageStatus.NOT_INSTALLED
                and not item.installing
                and not item.uninstalling
            ):
                items.append(item)
        return items

    def selected_uninstallable_items(self) -> list[ToolCardEntry]:
        items: list[ToolCardEntry] = []
        for item in self.tool_items:
            if (
                not item.card.is_checked()
                and item.status == PackageStatus.INSTALLED
                and not item.installing
                and not item.uninstalling
            ):
                items.append(item)
        return items

    def begin_install(self, items: list[ToolCardEntry]) -> list[Tool]:
        tools: list[Tool] = []
        for item in items:
            item.installing = True
            item.card.set_version_hint("Installing")
            tools.append(item.tool)
        return tools

    def begin_uninstall(self, items: list[ToolCardEntry]) -> list[Tool]:
        tools: list[Tool] = []
        for item in items:
            item.uninstalling = True
            item.card.set_version_hint("Uninstalling")
            tools.append(item.tool)
        return tools

    @staticmethod
    def tool_list_text(items: list[ToolCardEntry]) -> str:
        return "\n".join(f"- {item.tool.name} ({item.tool.package})" for item in items)
