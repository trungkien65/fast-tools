from __future__ import annotations

import shlex
import subprocess

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.core.installer import InstallResult, PackageInstaller
from app.core.package_checker import PackageChecker, PackageInfo, PackageStatus
from app.core.service_manager import ServiceManager
from app.core.tools_config import Tool, load_tools
from app.gui.component import (
    ActionBar,
    CommandConfirmDialog,
    FilterBar,
    LoadingMask,
    LogPanel,
    ToolCardEntry,
    ToolsTree,
)
from app.version import APP_NAME, get_app_version


class InstallWorker(QObject):
    log = Signal(str)
    finished = Signal(list)

    def __init__(self, tools: list[Tool]) -> None:
        super().__init__()
        self.tools = tools
        self.installer = PackageInstaller()

    @Slot()
    def run(self) -> None:
        results: list[InstallResult] = []
        for tool in self.tools:
            self.log.emit(f"Installing {tool.name} ({tool.package}) ...")
            result = self.installer.install_tool(tool)
            results.append(result)
            self.log.emit(result.message)
        self.finished.emit(results)


class UninstallWorker(QObject):
    log = Signal(str)
    finished = Signal(list)

    def __init__(self, tools: list[Tool]) -> None:
        super().__init__()
        self.tools = tools
        self.installer = PackageInstaller()

    @Slot()
    def run(self) -> None:
        results: list[InstallResult] = []
        for tool in self.tools:
            self.log.emit(f"Uninstalling {tool.name} ({tool.package}) ...")
            result = self.installer.uninstall_tool(tool)
            results.append(result)
            self.log.emit(result.message)
        self.finished.emit(results)


class RefreshWorker(QObject):
    log = Signal(str)
    checked = Signal(object, object, object, object)
    finished = Signal()

    def __init__(self, items: list[ToolCardEntry]) -> None:
        super().__init__()
        self.targets = [
            (item, item.tool.package, item.tool.command, item.tool.service)
            for item in items
        ]
        self.checker = PackageChecker()
        self.service_manager = ServiceManager()

    @Slot()
    def run(self) -> None:
        for item, package, command, service in self.targets:
            try:
                if item.tool.install_method == "apt":
                    package_info = self.checker.check_package(package, command)
                    status = package_info.status
                else:
                    installed = self.checker.command_exists(command) if command else False
                    status = PackageStatus.INSTALLED if installed else PackageStatus.NOT_INSTALLED
                    package_info = PackageInfo(
                        package=package,
                        installed=installed,
                        exists=True,
                        version="Detected in PATH" if installed else "",
                        command_available=installed if command else None,
                        status=status,
                    )
            except ValueError as exc:
                status = PackageStatus.PACKAGE_NOT_FOUND
                package_info = None
                self.log.emit(str(exc))

            service_info = self.service_manager.inspect(service) if service else None
            self.checked.emit(item, status, package_info, service_info)
        self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.app_version = get_app_version()
        self.setWindowTitle(f"{APP_NAME} v{self.app_version}")
        self.resize(1040, 640)

        self.tools: list[Tool] = load_tools()
        self.checker = PackageChecker()
        self.service_manager = ServiceManager()
        self._install_thread: QThread | None = None
        self._install_worker: InstallWorker | None = None
        self._uninstall_thread: QThread | None = None
        self._uninstall_worker: UninstallWorker | None = None
        self._refresh_thread: QThread | None = None
        self._refresh_worker: RefreshWorker | None = None

        self.filter_bar = FilterBar(self.tools)
        self.filter_bar.filters_changed.connect(self.apply_filters)
        self.tree = ToolsTree(self.tools)
        self.tree.toolbox_requested.connect(self.open_jetbrains_toolbox)
        self.action_bar = ActionBar()
        self.action_bar.refresh_requested.connect(self.refresh_statuses)
        self.action_bar.install_requested.connect(self.install_selected)
        self.action_bar.uninstall_requested.connect(self.uninstall_selected)
        self.log_panel = LogPanel()

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Developer tools"))
        layout.addWidget(self.filter_bar)
        layout.addWidget(self.tree)
        layout.addWidget(self.action_bar)
        layout.addWidget(self.log_panel)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.loading_mask = LoadingMask(central)

        self.refresh_statuses()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_loading_mask_geometry()

    def update_loading_mask_geometry(self) -> None:
        central = self.centralWidget()
        if central:
            self.loading_mask.setGeometry(central.rect())

    @Slot()
    def refresh_statuses(self) -> None:
        if self._refresh_thread and self._refresh_thread.isRunning():
            return

        self.append_log("Refreshing package statuses ...")
        self.set_buttons_enabled(False)
        self.show_loading("Refreshing package statuses...")
        self._refresh_thread = QThread(self)
        self._refresh_worker = RefreshWorker(self.tree.tool_items)
        self._refresh_worker.moveToThread(self._refresh_thread)
        self._refresh_thread.started.connect(self._refresh_worker.run)
        self._refresh_worker.log.connect(self.append_log)
        self._refresh_worker.checked.connect(self.update_refreshed_item)
        self._refresh_worker.finished.connect(self.refresh_finished)
        self._refresh_worker.finished.connect(self._refresh_thread.quit)
        self._refresh_worker.finished.connect(self._refresh_worker.deleteLater)
        self._refresh_thread.finished.connect(self.clear_refresh_worker)
        self._refresh_thread.finished.connect(self._refresh_thread.deleteLater)
        self._refresh_thread.start()

    @Slot(object, object, object, object)
    def update_refreshed_item(
        self,
        item: ToolCardEntry,
        status: PackageStatus,
        package_info: object | None,
        service_info: object | None,
    ) -> None:
        self.tree.update_package_status(item, status, package_info)
        self.tree.update_service_status(item, service_info)

    @Slot()
    def refresh_finished(self) -> None:
        self.set_buttons_enabled(True)
        self.apply_filters()
        self.hide_loading()
        self.append_log("Status refresh complete.", "success")

    @Slot()
    def clear_refresh_worker(self) -> None:
        self._refresh_thread = None
        self._refresh_worker = None

    @Slot()
    def install_selected(self) -> None:
        items = self.tree.selected_installable_items()
        if not items:
            QMessageBox.information(self, "Fast Tools", "No installable packages selected.")
            return

        if not self.confirm_package_action("Install", items):
            return

        selected_tools = self.tree.begin_install(items)
        self.set_buttons_enabled(False)
        self._install_thread = QThread(self)
        self._install_worker = InstallWorker(selected_tools)
        self._install_worker.moveToThread(self._install_thread)
        self._install_thread.started.connect(self._install_worker.run)
        self._install_worker.log.connect(self.append_log)
        self._install_worker.finished.connect(self.install_finished)
        self._install_worker.finished.connect(self._install_thread.quit)
        self._install_worker.finished.connect(self._install_worker.deleteLater)
        self._install_thread.finished.connect(self._install_thread.deleteLater)
        self._install_thread.start()

    @Slot()
    def uninstall_selected(self) -> None:
        items = self.tree.selected_uninstallable_items()
        if not items:
            QMessageBox.information(self, "Fast Tools", "No installed packages selected to uninstall.")
            return

        if not self.confirm_package_action("Uninstall", items):
            return

        selected_tools = self.tree.begin_uninstall(items)
        self.set_buttons_enabled(False)
        self._uninstall_thread = QThread(self)
        self._uninstall_worker = UninstallWorker(selected_tools)
        self._uninstall_worker.moveToThread(self._uninstall_thread)
        self._uninstall_thread.started.connect(self._uninstall_worker.run)
        self._uninstall_worker.log.connect(self.append_log)
        self._uninstall_worker.finished.connect(self.uninstall_finished)
        self._uninstall_worker.finished.connect(self._uninstall_thread.quit)
        self._uninstall_worker.finished.connect(self._uninstall_worker.deleteLater)
        self._uninstall_thread.finished.connect(self._uninstall_thread.deleteLater)
        self._uninstall_thread.start()

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

    @Slot(list)
    def uninstall_finished(self, results: list[InstallResult]) -> None:
        failures = [result for result in results if not result.success]
        self.refresh_statuses()
        if failures:
            QMessageBox.warning(
                self,
                "Fast Tools",
                f"{len(failures)} package(s) failed to uninstall. See the log for details.",
            )
        else:
            QMessageBox.information(
                self,
                "Fast Tools",
                "Selected packages uninstalled successfully.",
            )

    @Slot(str)
    def append_log(self, message: str, level: str = "info") -> None:
        self.log_panel.append(message, level)

    def set_buttons_enabled(self, enabled: bool) -> None:
        self.action_bar.set_controls_enabled(enabled)
        self.filter_bar.set_controls_enabled(enabled)

    def show_loading(self, message: str) -> None:
        self.update_loading_mask_geometry()
        self.loading_mask.show_message(message)

    def hide_loading(self) -> None:
        self.loading_mask.hide()

    def confirm_package_action(
        self,
        action_label: str,
        items: list[ToolCardEntry],
    ) -> bool:
        command = self.generated_action_preview(action_label, items)
        dialog = CommandConfirmDialog(
            f"{action_label} {len(items)} selected package(s)?",
            self.tree.tool_list_text(items),
            command,
            self,
        )
        accepted = dialog.exec() == CommandConfirmDialog.DialogCode.Accepted
        if accepted:
            self.append_log(command)
        return accepted

    def generated_action_preview(self, action_label: str, items: list[ToolCardEntry]) -> str:
        lines: list[str] = []
        is_install = action_label.lower() == "install"
        for item in items:
            tool = item.tool
            command = self.preview_command_for_tool(tool, is_install=is_install)
            lines.append(f"# {tool.name} ({tool.package})")
            lines.append(command)
        return "\n".join(lines)

    @staticmethod
    def preview_command_for_tool(tool: Tool, is_install: bool) -> str:
        if tool.install_method == "apt":
            apt_action = "install" if is_install else "remove"
            package_name = tool.package
            return shlex.join(["sudo", "apt", apt_action, "-y", package_name])
        if tool.install_method == "deb_url":
            if is_install:
                return shlex.join(["sudo", "apt", "install", "-y", tool.deb_url or "<deb_url>"])
            package_name = tool.uninstall_package.strip() or tool.package
            return shlex.join(["sudo", "apt", "remove", "-y", package_name])
        command = tool.install_command if is_install else tool.uninstall_command
        return command.strip() or "# No command configured"

    @Slot()
    def open_jetbrains_toolbox(self) -> None:
        launch_commands = (
            ["jetbrains-toolbox"],
            ["gtk-launch", "jetbrains-toolbox"],
            ["xdg-open", "jetbrains-toolbox://"],
        )
        for command in launch_commands:
            try:
                subprocess.Popen(command)
                self.append_log("Opening JetBrains Toolbox ...")
                return
            except FileNotFoundError:
                continue
            except OSError as exc:
                self.append_log(f"Failed to launch JetBrains Toolbox with {' '.join(command)}: {exc}")

        QMessageBox.warning(
            self,
            "Fast Tools",
            "Could not open JetBrains Toolbox. Please install or launch it manually.",
        )

    @Slot()
    def apply_filters(self) -> None:
        self.tree.apply_filters(self.filter_bar.search_text, self.filter_bar.selected_category)
