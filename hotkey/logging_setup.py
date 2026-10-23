"""日志与全局异常捕获，编辑器与监听器共用。"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QtMsgType, qInstallMessageHandler

from hotkey.core import storage

logger = logging.getLogger("HotKey.Logging")

_QT_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}


def configure_logging(filename: str = "hotkey.log") -> Path | None:
    """把日志写到配置目录 logs/；文件不可写时只保留 stderr。"""
    log_dir = storage.config_root() / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            log_dir / filename,
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


def install_exception_logging() -> None:
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


def install_qt_logging() -> None:
    def handler(mode, context, message: str) -> None:
        level = _QT_LEVELS.get(mode, logging.INFO)
        logger.log(level, "Qt: %s", message)

    qInstallMessageHandler(handler)
