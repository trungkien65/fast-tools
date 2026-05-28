from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget


class LoadingMask(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingMask")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setVisible(False)

        self.label = QLabel("Loading...")
        self.label.setObjectName("loadingMaskLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(260)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        layout.addWidget(self.label)
        layout.addWidget(self.progress, 0, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QFrame#loadingMask {
                background: rgba(255, 255, 255, 210);
                border: 1px solid #e5e7eb;
            }
            QLabel#loadingMaskLabel {
                color: #111827;
                font-weight: 700;
            }
            """
        )

    def show_message(self, message: str) -> None:
        self.label.setText(message)
        self.show()
        self.raise_()
