from __future__ import annotations

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget


class LogPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(150)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.output)
        self.setLayout(layout)

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
