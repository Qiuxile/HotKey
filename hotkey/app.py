"""应用启动与生命周期。"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from hotkey.core import storage
from hotkey.ui.main_window import MainWindow

APP_NAME = "HotKey"
SERVER_NAME = "HotKey.SingleInstance.v2"

logger = logging.getLogger("HotKey.App")

_QT_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}


def _theme_path() -> Path:
    """源码运行与 PyInstaller 冻结后都能找到 QSS。"""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "hotkey" / "ui" / "theme.qss"
    return Path(__file__).resolve().parent / "ui" / "theme.qss"


def configure_logging() -> Path | None:
    log_dir = storage.config_root() / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_dir / "hotkey.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
    except OSError:
        handler = None
        log_dir = None

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if handler is not None:
        handler.setFormatter(formatter)
        root.addHandler(handler)

    if sys.stderr is not None:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        root.addHandler(stream)

    return log_dir


def _install_exception_logging() -> None:
    def handle(exc_type, exc_value, exc_traceback) -> None:
        logger.critical(
            "未捕获异常",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle

    def handle_thread(args) -> None:
        logger.critical(
            "线程 %s 未捕获异常",
            args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = handle_thread


def _install_qt_logging() -> None:
    def handler(mode, context, message: str) -> None:
        level = _QT_LEVELS.get(mode, logging.INFO)
        logger.log(level, "Qt: %s", message)

    qInstallMessageHandler(handler)


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
    _install_exception_logging()
    logger.info("HotKey 启动，配置目录: %s", storage.config_root())

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    _install_qt_logging()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(True)

    theme = _theme_path()
    if theme.exists():
        app.setStyleSheet(theme.read_text(encoding="utf-8"))

    if not self_test and _notify_existing_instance():
        logger.info("已有实例在运行，已激活该窗口")
        return 0

    window = MainWindow()
    app.setWindowIcon(window._make_icon())
    server = _create_instance_server(window)  # noqa: F841 - 需要保持引用
    window.show()

    if self_test:
        QTimer.singleShot(300, app.quit)

    return app.exec()
