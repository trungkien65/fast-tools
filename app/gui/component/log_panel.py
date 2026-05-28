from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QToolButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)


class LogPanel(QWidget):
    EXPANDED_HEIGHT = 300

    def __init__(self) -> None:
        super().__init__()
        self.expanded = False

        self.title = QLabel("Log")
        self.title.setObjectName("logPanelTitle")

        self.toggle_button = QToolButton()
        self.toggle_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_button.setObjectName("logPanelToggle")
        self.toggle_button.setIconSize(QSize(14, 14))
        self.toggle_button.clicked.connect(self.toggle_expanded)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(self.toggle_button)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumHeight(self.EXPANDED_HEIGHT)
        self.output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(self.output)
        self.setLayout(layout)
        self.setStyleSheet(
            """
            QLabel#logPanelTitle {
                font-weight: 700;
            }
            QToolButton#logPanelToggle {
                border: none;
                padding: 2px;
                background: transparent;
            }
            QToolButton#logPanelToggle:hover {
                background: #eef2ff;
            }
            """
        )
        self.set_expanded(False)

    def toggle_expanded(self) -> None:
        self.set_expanded(not self.expanded)

    def set_expanded(self, expanded: bool) -> None:
        self.expanded = expanded
        self.output.setVisible(expanded)
        self.output.setMaximumHeight(self.EXPANDED_HEIGHT)
        icon = (
            QStyle.StandardPixmap.SP_ArrowUp
            if expanded
            else QStyle.StandardPixmap.SP_ArrowDown
        )
        label = "Collapse log" if expanded else "Expand log"
        self.toggle_button.setIcon(self.style().standardIcon(icon))
        self.toggle_button.setToolTip(label)
        self.toggle_button.setAccessibleName(label)

    def append(self, message: str, level: str = "info") -> None:
        color = {
            "success": "#166534",
            "error": "#991b1b",
        }.get(level)
        if color:
            self.output.append(f'<span style="color:{color};">{message}</span>')
        else:
            self.output.append(message)
        self.output.moveCursor(QTextCursor.MoveOperation.End)
