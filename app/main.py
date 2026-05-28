import sys

from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow


def main() -> int:
    if "--smoke-test" in sys.argv:
        app = QApplication([arg for arg in sys.argv if arg != "--smoke-test"])
        window = MainWindow(auto_refresh=False)
        window.close()
        app.quit()
        print("Fast Tools Qt startup ok")
        return 0

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
