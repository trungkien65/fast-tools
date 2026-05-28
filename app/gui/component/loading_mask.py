from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class Spinner(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.angle = 0
        self.setFixedSize(36, 36)
        self.timer = QTimer(self)
        self.timer.setInterval(24)
        self.timer.timeout.connect(self.rotate)

    def start(self) -> None:
        if not self.timer.isActive():
            self.timer.start()

    def stop(self) -> None:
        self.timer.stop()

    def rotate(self) -> None:
        self.angle = (self.angle + 12) % 360
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#2563eb"), 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        rect = QRectF(5, 5, self.width() - 10, self.height() - 10)
        painter.drawArc(rect, int(-self.angle * 16), int(110 * 16))


class LoadingMask(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingMask")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.label = QLabel("Loading...")
        self.label.setObjectName("loadingMaskLabel")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner = Spinner()

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.setStyleSheet(
            """
            QFrame#loadingMask {
                background: rgba(255, 255, 255, 150);
                border: 1px solid #e5e7eb;
            }
            QLabel#loadingMaskLabel {
                color: #111827;
                font-weight: 700;
            }
            """
        )
        self.setVisible(False)

    def show_message(self, message: str) -> None:
        self.label.setText(message)
        self.spinner.start()
        self.show()
        self.raise_()

    def hideEvent(self, event) -> None:
        self.spinner.stop()
        super().hideEvent(event)
