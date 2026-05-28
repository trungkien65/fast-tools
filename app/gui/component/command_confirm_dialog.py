from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QStyle,
    QToolButton,
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
        self.display_command = command
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

        self.one_line_checkbox = QCheckBox("One line")
        self.one_line_checkbox.setObjectName("commandOption")
        self.one_line_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.one_line_checkbox.toggled.connect(self.update_command_block)

        self.copy_button = QToolButton()
        self.copy_button.setObjectName("commandCopyButton")
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_button.setToolTip("Copy command")
        self.copy_button.setAccessibleName("Copy command")
        self.copy_button.setIcon(
            QIcon.fromTheme(
                "edit-copy",
                self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon),
            )
        )
        self.copy_button.setIconSize(QSize(12, 12))
        self.copy_button.clicked.connect(self.copy_command)

        command_header = QHBoxLayout()
        command_header.setContentsMargins(0, 0, 0, 0)
        command_header.addWidget(command_label)
        command_header.addStretch()

        command_container = QWidget()
        command_container.setObjectName("commandContainer")
        command_tools = QWidget()
        command_tools.setObjectName("commandTools")
        command_tools_layout = QHBoxLayout()
        command_tools_layout.setContentsMargins(0, 0, 0, 0)
        command_tools_layout.setSpacing(6)
        command_tools_layout.addWidget(self.one_line_checkbox)
        command_tools_layout.addWidget(self.copy_button)
        command_tools.setLayout(command_tools_layout)

        command_layout = QGridLayout()
        command_layout.setContentsMargins(0, 0, 0, 0)
        command_layout.addWidget(self.command_block, 0, 0)
        command_layout.addWidget(
            command_tools,
            0,
            0,
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
        )
        command_container.setLayout(command_layout)

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
        layout.addWidget(command_container)
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
                padding: 32px 8px 8px 8px;
            }
            QWidget#commandTools {
                background: rgba(31, 41, 55, 225);
                border: 1px solid #4b5563;
                border-radius: 4px;
                margin: 6px;
                padding: 2px;
            }
            QCheckBox#commandOption {
                color: #f9fafb;
                font-size: 11px;
                spacing: 4px;
            }
            QToolButton#commandCopyButton {
                background: transparent;
                border: none;
                padding: 2px;
            }
            QToolButton#commandCopyButton:hover {
                background: #374151;
            }
            """
        )

    def update_command_block(self) -> None:
        self.display_command = self.formatted_command()
        self.command_block.setPlainText(self.display_command)
        self.copy_button.setToolTip("Copy command")
        self.copy_button.setAccessibleName("Copy command")

    def formatted_command(self) -> str:
        if not self.one_line_checkbox.isChecked():
            return self.command

        commands = [
            line.strip()
            for line in self.command.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        return " && ".join(commands)

    def copy_command(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.display_command)
        self.copy_button.setToolTip("Copied")
        self.copy_button.setAccessibleName("Copied")
