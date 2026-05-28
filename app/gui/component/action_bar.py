from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget


class ActionBar(QWidget):
    refresh_requested = Signal()
    install_requested = Signal()
    uninstall_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_button.clicked.connect(self.refresh_requested)

        self.install_button = QPushButton("Install selected")
        self.install_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_button.clicked.connect(self.install_requested)

        self.uninstall_button = QPushButton("Uninstall selected")
        self.uninstall_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.uninstall_button.clicked.connect(self.uninstall_requested)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.install_button)
        layout.addWidget(self.uninstall_button)
        layout.addStretch()
        self.setLayout(layout)

    def set_controls_enabled(self, enabled: bool) -> None:
        self.refresh_button.setEnabled(enabled)
        self.install_button.setEnabled(enabled)
        self.uninstall_button.setEnabled(enabled)
