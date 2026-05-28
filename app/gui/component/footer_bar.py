from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QStyle, QToolButton, QWidget


class FooterBar(QWidget):
    update_requested = Signal()

    def __init__(self, version_text: str) -> None:
        super().__init__()

        self.version_label = QLabel(version_text)
        self.version_label.setObjectName("footerVersionLabel")

        self.update_button = QToolButton()
        self.update_button.setObjectName("footerUpdateButton")
        self.update_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_button.setToolTip("Update Fast Tools")
        self.update_button.setAccessibleName("Update Fast Tools")
        self.update_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.update_button.setIconSize(QSize(12, 12))
        self.update_button.clicked.connect(self.update_requested)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.version_label)
        layout.addWidget(self.update_button)
        layout.addStretch()
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QLabel#footerVersionLabel {
                color: #6b7280;
                font-size: 12px;
            }
            QToolButton#footerUpdateButton {
                border: none;
                padding: 0;
                background: transparent;
            }
            QToolButton#footerUpdateButton:hover {
                background: transparent;
            }
            QToolButton#footerUpdateButton:disabled {
                background: transparent;
                color: #9ca3af;
            }
            """
        )

    def set_controls_enabled(self, enabled: bool) -> None:
        self.update_button.setEnabled(enabled)
