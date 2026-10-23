"""应用启动与生命周期。"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from hotkey.core import storage
from hotkey import __version__
from hotkey.logging_setup import (
    configure_logging,
    install_exception_logging,
    install_qt_logging,
)
from hotkey.ui.icon import app_icon
from hotkey.ui.main_window import MainWindow
from hotkey.ui.theme import apply_theme

APP_NAME = "HotKey"
SERVER_NAME = "HotKey.SingleInstance.v2"

logger = logging.getLogger("HotKey.App")


def _notify_existing_instance() -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if not socket.waitForConnected(300):
        return False
    socket.write(b"show")
    socket.flush()
    socket.waitForBytesWritten(300)
    socket.disconnectFromServer()
    return True


def _create_instance_server(window: MainWindow) -> QLocalServer | None:
    server = QLocalServer(window)
    QLocalServer.removeServer(SERVER_NAME)
    if not server.listen(SERVER_NAME):
        logger.warning("单实例服务启动失败: %s", server.errorString())
        return None

    def handle_connection() -> None:
        connection = server.nextPendingConnection()
        if connection is not None:
            connection.disconnected.connect(connection.deleteLater)
        window.showNormal()
        window.raise_()
        window.activateWindow()

    server.newConnection.connect(handle_connection)
    return server


def run(self_test: bool = False) -> int:
    configure_logging()
    install_exception_logging()
    logger.info("HotKey 启动，配置目录: %s", storage.config_root())

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    install_qt_logging()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(True)

    apply_theme(app)

    if not self_test and _notify_existing_instance():
        logger.info("已有实例在运行，已激活该窗口")
        return 0

    window = MainWindow()
    app.setWindowIcon(app_icon())
    server = _create_instance_server(window)  # noqa: F841 - 需要保持引用
    window.show()

    if self_test:
        QTimer.singleShot(300, app.quit)

    return app.exec()
