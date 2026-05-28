from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CommandConfirmDialog(QDialog):
    def __init__(
        self,
        action_label: str,
        items_text: str,
        command: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.command = command
        self.setWindowTitle("Fast Tools")
        self.setMinimumWidth(560)

        title = QLabel(action_label)
        title.setObjectName("commandDialogTitle")

        items = QLabel(items_text)
        items.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        command_label = QLabel("Command")
        command_label.setObjectName("commandDialogLabel")

        self.command_block = QTextEdit()
        self.command_block.setReadOnly(True)
        self.command_block.setPlainText(command)
        self.command_block.setFixedHeight(76)
        self.command_block.setObjectName("commandBlock")

        self.copy_button = QPushButton("Copy")
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.clicked.connect(self.copy_command)

        command_header = QHBoxLayout()
        command_header.setContentsMargins(0, 0, 0, 0)
        command_header.addWidget(command_label)
        command_header.addStretch()
        command_header.addWidget(self.copy_button)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel,
        )
        self.run_button = self.buttons.addButton(
            action_label,
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.run_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button:
            cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(items)
        layout.addLayout(command_header)
        layout.addWidget(self.command_block)
        layout.addWidget(self.buttons)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QLabel#commandDialogTitle {
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#commandDialogLabel {
                font-weight: 700;
            }
            QTextEdit#commandBlock {
                background: #111827;
                border: 1px solid #374151;
                border-radius: 6px;
                color: #f9fafb;
                font-family: monospace;
                padding: 8px;
            }
            """
        )

    def copy_command(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.command)
        self.copy_button.setText("Copied")
