from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from app.gui.component.constants import CARD_MAX_WIDTH, CARD_MIN_WIDTH


class ToolCard(QFrame):
    checked_changed = Signal(bool)

    def __init__(
        self,
        tool_name: str,
        version_hint: str = "Checking...",
        description: str = "",
    ) -> None:
        super().__init__()
        self.description = description

        self.checkbox = QCheckBox()
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.toggled.connect(self.checked_changed.emit)

        self.name_label = QLabel(tool_name)
        self.name_label.setObjectName("toolCardName")

        self.info_button = QPushButton("i")
        self.info_button.setObjectName("toolInfoButton")
        self.info_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.info_button.setFixedSize(14, 14)
        self.info_button.clicked.connect(self.show_description)
        self.set_description(description)

        name_layout = QHBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(4)
        name_layout.addWidget(self.name_label)
        name_layout.addWidget(
            self.info_button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )
        name_layout.addStretch()

        self.version_hint_label = QLabel(version_hint)
        self.version_hint_label.setObjectName("toolCardVersion")

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text_layout.addLayout(name_layout)
        text_layout.addWidget(self.version_hint_label)

        self.text_container = QWidget()
        self.text_container.setLayout(text_layout)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        layout.addWidget(
            self.checkbox,
            0,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        layout.addWidget(
            self.text_container,
            1,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )
        self.setLayout(layout)

        self.setMinimumWidth(CARD_MIN_WIDTH)
        self.setMaximumWidth(CARD_MAX_WIDTH)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setObjectName("toolCard")
        self.setStyleSheet(
            """
            QPushButton#toolInfoButton {
                background: #eef2ff;
                border: 1px solid #c7d2fe;
                border-radius: 7px;
                color: #3730a3;
                font-size: 9px;
                font-weight: 700;
                padding: 0;
            }
            QPushButton#toolInfoButton:hover {
                background: #e0e7ff;
            }
            QLabel#toolCardVersion {
                color: #6b7280;
                font-size: 12px;
            }
            """
        )

    def is_checked(self) -> bool:
        return self.checkbox.isChecked()

    def set_checked(self, checked: bool) -> None:
        self.checkbox.setChecked(checked)

    def set_checkbox_enabled(self, enabled: bool) -> None:
        self.checkbox.setEnabled(enabled)
        cursor = (
            Qt.CursorShape.PointingHandCursor
            if enabled
            else Qt.CursorShape.ArrowCursor
        )
        self.checkbox.setCursor(cursor)

    def set_tool_name(self, tool_name: str) -> None:
        self.name_label.setText(tool_name)

    def set_description(self, description: str) -> None:
        self.description = description
        self.info_button.setToolTip(description)
        self.info_button.setVisible(bool(description))

    def show_description(self) -> None:
        if not self.description:
            return
        position = self.info_button.mapToGlobal(self.info_button.rect().bottomLeft())
        QToolTip.showText(position, self.description, self.info_button)

    def set_version_hint(self, version_hint: str) -> None:
        self.version_hint_label.setText(version_hint)
