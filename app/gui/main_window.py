from __future__ import annotations

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from app.core.installer import InstallResult, PackageInstaller
from app.core.package_checker import PackageChecker, PackageStatus
from app.core.service_manager import ServiceManager
from app.core.tools_config import Tool, load_tools


class InstallWorker(QObject):
    log = Signal(str)
    finished = Signal(list)

    def __init__(self, packages: list[str]) -> None:
        super().__init__()
        self.packages = packages
        self.installer = PackageInstaller()

    @Slot()
    def run(self) -> None:
        results: list[InstallResult] = []
        for package in self.packages:
            self.log.emit(f"Installing {package} ...")
            result = self.installer.install(package)
            results.append(result)
            self.log.emit(result.message)
        self.finished.emit(results)


class MainWindow(QMainWindow):
    PACKAGE_ROLE = 256
    NAME_ROLE = 257
    CATEGORY_ROLE = 258
    SERVICE_ROLE = 259
    COMMAND_ROLE = 260

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fast Tools")
        self.resize(1040, 640)

        self.tools: list[Tool] = load_tools()
        self.checker = PackageChecker()
        self.service_manager = ServiceManager()
        self._install_thread: QThread | None = None
        self._install_worker: InstallWorker | None = None

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search name or package")
        self.search_input.textChanged.connect(self.apply_filters)

        self.category_filter = QComboBox()
        self.category_filter.addItem("All categories")
        for category in sorted({tool.category for tool in self.tools}):
            self.category_filter.addItem(category)
        self.category_filter.currentTextChanged.connect(self.apply_filters)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Package", "Category", "Status", "Version", "Service"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_statuses)

        self.install_button = QPushButton("Install selected")
        self.install_button.clicked.connect(self.install_selected)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(150)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.category_filter)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.install_button)
        button_layout.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Developer tools"))
        layout.addLayout(filter_layout)
        layout.addWidget(self.table)
        layout.addLayout(button_layout)
        layout.addWidget(QLabel("Log"))
        layout.addWidget(self.log_output)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.populate_table()
        self.refresh_statuses()

    def populate_table(self) -> None:
        self.table.setRowCount(len(self.tools))
        for row, tool in enumerate(self.tools):
            name_item = QTableWidgetItem(tool.name)
            name_item.setCheckState(Qt.CheckState.Unchecked)
            name_item.setData(self.NAME_ROLE, tool.name)
            name_item.setData(self.PACKAGE_ROLE, tool.package)
            name_item.setData(self.CATEGORY_ROLE, tool.category)
            name_item.setData(self.SERVICE_ROLE, tool.service)
            name_item.setData(self.COMMAND_ROLE, tool.command)
            if tool.description:
                name_item.setToolTip(tool.description)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QTableWidgetItem(tool.package))
            self.table.setItem(row, 2, QTableWidgetItem(tool.category))
            self.table.setItem(row, 3, QTableWidgetItem("Checking..."))
            self.table.setItem(row, 4, QTableWidgetItem(""))
            self.table.setItem(row, 5, QTableWidgetItem(""))

    @Slot()
    def refresh_statuses(self) -> None:
        self.append_log("Refreshing package statuses ...")
        self.set_buttons_enabled(False)
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            status_item = self.table.item(row, 3)
            version_item = self.table.item(row, 4)
            service_item = self.table.item(row, 5)
            package = name_item.data(self.PACKAGE_ROLE)
            command = name_item.data(self.COMMAND_ROLE)
            service = name_item.data(self.SERVICE_ROLE)
            try:
                package_info = self.checker.check_package(package, command)
                status = package_info.status
            except ValueError as exc:
                status = PackageStatus.PACKAGE_NOT_FOUND
                package_info = None
                self.append_log(str(exc))

            status_item.setText(status.value)
            version_item.setText(package_info.version if package_info else "")
            name_item.setCheckState(
                Qt.CheckState.Checked
                if status == PackageStatus.INSTALLED
                else Qt.CheckState.Unchecked
            )
            name_item.setFlags(name_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if status == PackageStatus.INSTALLED:
                name_item.setToolTip("Already installed")
            elif status == PackageStatus.PACKAGE_NOT_FOUND:
                name_item.setToolTip("Package was not found by apt-cache")
            else:
                name_item.setToolTip("Select to install")

            if service:
                service_info = self.service_manager.inspect(service)
                if service_info.exists:
                    enabled = "enabled" if service_info.enabled else "disabled"
                    service_item.setText(f"{service_info.active_state.value}, {enabled}")
                else:
                    service_item.setText("Not Found")
            else:
                service_item.setText("")

        self.set_buttons_enabled(True)
        self.apply_filters()
        self.append_log("Status refresh complete.", "success")

    @Slot()
    def install_selected(self) -> None:
        packages = self.selected_installable_packages()
        if not packages:
            QMessageBox.information(self, "Fast Tools", "No installable packages selected.")
            return

        self.set_buttons_enabled(False)
        self._install_thread = QThread(self)
        self._install_worker = InstallWorker(packages)
        self._install_worker.moveToThread(self._install_thread)
        self._install_thread.started.connect(self._install_worker.run)
        self._install_worker.log.connect(self.append_log)
        self._install_worker.finished.connect(self.install_finished)
        self._install_worker.finished.connect(self._install_thread.quit)
        self._install_worker.finished.connect(self._install_worker.deleteLater)
        self._install_thread.finished.connect(self._install_thread.deleteLater)
        self._install_thread.start()

    def selected_installable_packages(self) -> list[str]:
        packages: list[str] = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            status_item = self.table.item(row, 3)
            if (
                name_item.checkState() == Qt.CheckState.Checked
                and status_item.text() == PackageStatus.NOT_INSTALLED.value
            ):
                status_item.setText("Installing")
                packages.append(name_item.data(self.PACKAGE_ROLE))
        return packages

    @Slot(list)
    def install_finished(self, results: list[InstallResult]) -> None:
        failures = [result for result in results if not result.success]
        self.refresh_statuses()
        if failures:
            QMessageBox.warning(
                self,
                "Fast Tools",
                f"{len(failures)} package(s) failed to install. See the log for details.",
            )
        else:
            QMessageBox.information(self, "Fast Tools", "Selected packages installed successfully.")

    @Slot(str)
    def append_log(self, message: str, level: str = "info") -> None:
        color = {
            "success": "#166534",
            "error": "#991b1b",
            "info": "#111827",
        }.get(level, "#111827")
        self.log_output.append(f'<span style="color:{color};">{message}</span>')
        self.log_output.moveCursor(QTextCursor.MoveOperation.End)

    def set_buttons_enabled(self, enabled: bool) -> None:
        self.refresh_button.setEnabled(enabled)
        self.install_button.setEnabled(enabled)
        self.search_input.setEnabled(enabled)
        self.category_filter.setEnabled(enabled)

    @Slot()
    def apply_filters(self) -> None:
        search = self.search_input.text().strip().lower()
        category = self.category_filter.currentText()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            package = name_item.data(self.PACKAGE_ROLE).lower()
            name = name_item.data(self.NAME_ROLE).lower()
            row_category = name_item.data(self.CATEGORY_ROLE)
            matches_search = not search or search in name or search in package
            matches_category = category == "All categories" or category == row_category
            self.table.setRowHidden(row, not (matches_search and matches_category))
