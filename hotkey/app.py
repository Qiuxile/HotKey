"""应用启动与生命周期。"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from hotkey.ui.main_window import MainWindow

APP_NAME = "HotKey"


def _theme_path() -> Path:
    """源码运行与 PyInstaller 冻结后都能找到 QSS。"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "hotkey" / "ui" / "theme.qss"
    return Path(__file__).resolve().parent / "ui" / "theme.qss"


def run(self_test: bool = False) -> int:
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(True)

    theme = _theme_path()
    if theme.exists():
        app.setStyleSheet(theme.read_text(encoding="utf-8"))

    window = MainWindow()
    window.show()

    if self_test:
        QTimer.singleShot(200, app.quit)

    return app.exec()
