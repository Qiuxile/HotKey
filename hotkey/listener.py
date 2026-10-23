"""独立的全局热键监听器进程。

编辑器只负责编辑；监听器负责常驻后台、注册热键、执行脚本和托盘。
两者都读写同一个 ``jsons/`` 脚本库，通过 .hk 文件同步。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, QProcess, QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from hotkey.core.hotkey_service import HotkeyService
from hotkey.core.library import ScriptLibrary, default_script_dir
from hotkey.core.models import HotKey
from hotkey.core.runner import ScriptRunner
from hotkey.logging_setup import (
    configure_logging,
    install_exception_logging,
    install_qt_logging,
)
from hotkey.ui.icon import app_icon

APP_NAME = "HotKey"
LISTENER_SERVER = "HotKey.Listener.v1"
RELOAD_DELAY_MS = 350

logger = logging.getLogger("HotKey.Listener")


def _command(command: str, timeout_ms: int = 400) -> str | None:
    """向已运行的监听器发命令；没有监听器时返回 None。"""
    socket = QLocalSocket()
    socket.connectToServer(LISTENER_SERVER)
    if not socket.waitForConnected(timeout_ms):
        return None
    socket.write(command.encode("utf-8"))
    socket.flush()
    socket.waitForBytesWritten(timeout_ms)
    response = ""
    if socket.waitForReadyRead(timeout_ms):
        response = bytes(socket.readAll()).decode("utf-8", errors="replace")
    socket.disconnectFromServer()
    return response


def is_listener_running() -> bool:
    return _command("status") is not None


def stop_listener() -> bool:
    return _command("quit") is not None


def launch_listener() -> bool:
    """启动同一程序/脚本的 --listen 模式。"""
    if is_listener_running():
        return True
    if getattr(sys, "frozen", False):
        program = sys.executable
        arguments: list[str] = ["--listen"]
    else:
        program = sys.executable
        arguments = [str(Path(__file__).resolve().parents[1] / "main.py"), "--listen"]
    started, _pid = QProcess.startDetached(program, arguments)
    return started


def launch_editor() -> bool:
    """从托盘打开编辑器（单实例逻辑由编辑器自己处理）。"""
    if getattr(sys, "frozen", False):
        program = sys.executable
        arguments: list[str] = []
    else:
        program = sys.executable
        arguments = [str(Path(__file__).resolve().parents[1] / "main.py")]
    started, _pid = QProcess.startDetached(program, arguments)
    return started


class _Signals(QObject):
    triggered = Signal(str)
    started = Signal(str)
    finished = Signal(str, bool, str)
    hotkey_error = Signal(str, str)


class ListenerApp(QObject):
    """常驻监听器：托盘 + 文件监视 + 热键服务 + 脚本执行。"""

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app
        self._library = ScriptLibrary(default_script_dir())
        self._scripts: dict[str, HotKey] = {}
        self._paused = False
        self._shutting_down = False

        self._signals = _Signals(self)
        self._runner = ScriptRunner(
            on_started=self._signals.started.emit,
            on_finished=self._signals.finished.emit,
        )
        self._service = HotkeyService(
            on_trigger=self._signals.triggered.emit,
            on_error=self._signals.hotkey_error.emit,
        )

        self._tray: QSystemTrayIcon | None = None
        self._tray_menu: QMenu | None = None
        self._pause_action = None
        self._watcher = QFileSystemWatcher(self)
        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(RELOAD_DELAY_MS)
        self._reload_timer.timeout.connect(self.reload)

        self._server = QLocalServer(self)
        self._setup_signals()
        self._setup_tray()
        self._setup_server()
        self._setup_watcher()
        self.reload()

    # ---------------------------------------------------------------- 初始化

    def _setup_signals(self) -> None:
        self._signals.triggered.connect(self._execute)
        self._signals.finished.connect(self._on_finished)
        self._signals.hotkey_error.connect(self._on_hotkey_error)
        self._app.aboutToQuit.connect(self._shutdown)

    def _setup_watcher(self) -> None:
        self._watcher.directoryChanged.connect(self._schedule_reload)
        self._watcher.fileChanged.connect(self._schedule_reload)

    def _schedule_reload(self, _path: str = "") -> None:
        self._reload_timer.start()

    def _setup_server(self) -> None:
        if not self._server.listen(LISTENER_SERVER):
            QLocalServer.removeServer(LISTENER_SERVER)
            if not self._server.listen(LISTENER_SERVER):
                logger.error("监听器单实例服务启动失败: %s", self._server.errorString())
                return
        self._server.newConnection.connect(self._accept_connection)

    def _accept_connection(self) -> None:
        connection = self._server.nextPendingConnection()
        if connection is None:
            return
        connection.readyRead.connect(
            lambda: self._handle_command(connection)
        )
        connection.disconnected.connect(connection.deleteLater)

    def _handle_command(self, connection: QLocalSocket) -> None:
        command = bytes(connection.readAll()).decode(
            "utf-8", errors="replace"
        ).strip()
        if command == "status":
            state = "paused" if self._paused else "running"
            connection.write(state.encode("utf-8"))
        elif command == "reload":
            self.reload()
            connection.write(b"ok")
        elif command == "quit":
            connection.write(b"bye")
            connection.flush()
            self.shutdown()
            return
        connection.flush()

    # ---------------------------------------------------------------- 脚本库

    def reload(self) -> None:
        """重新扫描脚本库，并把热键注册更新到最新。"""
        scripts = self._library.load()
        self._scripts = {
            script.id: script
            for script in scripts
            if script.enabled and script.key and script.script.strip()
        }
        if self._library.warnings:
            logger.info("脚本库: %s", "；".join(self._library.warnings))
        self._refresh_service()
        self._refresh_watcher()
        self._update_tray()

    def _refresh_service(self) -> None:
        self._service.stop()
        if self._paused or not self._scripts:
            return
        try:
            self._service.start(self._scripts.values())
        except Exception as exc:  # noqa: BLE001
            logger.exception("监听器启动热键失败")
            self._show_message("热键注册失败", str(exc), warning=True)

    def _refresh_watcher(self) -> None:
        directory = str(self._library.directory)
        wanted = {directory}
        wanted.update(str(path) for path in self._library.directory.glob("*.hk"))
        current = set(self._watcher.files()) | set(self._watcher.directories())
        remove = current - wanted
        add = wanted - current
        if remove:
            self._watcher.removePaths(sorted(remove))
        if add:
            self._watcher.addPaths(sorted(add))

    # ---------------------------------------------------------------- 执行

    def _execute(self, hotkey_id: str) -> None:
        script = self._scripts.get(hotkey_id)
        if script is None:
            return
        self._runner.submit(hotkey_id, script.script)

    def _on_finished(self, hotkey_id: str, ok: bool, message: str) -> None:
        if ok:
            return
        script = self._scripts.get(hotkey_id)
        name = script.name if script else hotkey_id
        logger.error("脚本 %s 执行失败: %s", name, message)
        self._show_message("脚本执行失败", f"{name}\n{message}", warning=True)

    def _on_hotkey_error(self, key: str, message: str) -> None:
        logger.error("热键 %s 注册失败: %s", key, message)
        self._show_message("热键注册失败", f"{key}\n{message}", warning=True)

    # ---------------------------------------------------------------- 托盘

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("系统托盘不可用，监听器仍会后台运行")
            return

        menu = QMenu()
        self._tray_menu = menu
        open_action = menu.addAction("打开编辑器")
        open_action.triggered.connect(launch_editor)
        menu.addSeparator()
        self._pause_action = menu.addAction("暂停监听")
        self._pause_action.triggered.connect(self.toggle_pause)
        menu.addSeparator()
        quit_action = menu.addAction("退出监听器")
        quit_action.triggered.connect(self.shutdown)

        self._tray = QSystemTrayIcon(app_icon(), self)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _on_tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            launch_editor()

    def _update_tray(self) -> None:
        if self._tray is None:
            return
        if self._paused:
            state = "已暂停"
        elif self._scripts:
            state = f"{len(self._scripts)} 个热键"
        else:
            state = "没有可运行的热键"
        self._tray.setToolTip(f"HotKey 监听器 · {state}")
        if self._pause_action is not None:
            self._pause_action.setText(
                "继续监听" if self._paused else "暂停监听"
            )

    def _show_message(self, title: str, message: str, warning: bool = False) -> None:
        if self._tray is None:
            return
        icon = (
            QSystemTrayIcon.MessageIcon.Warning
            if warning
            else QSystemTrayIcon.MessageIcon.Information
        )
        self._tray.showMessage(title, message, icon, 4000)

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        self._refresh_service()
        self._update_tray()

    # ---------------------------------------------------------------- 退出

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        self._service.stop()
        self._runner.shutdown()
        if self._tray is not None:
            self._tray.hide()
        self._server.close()
        self._app.quit()

    def _shutdown(self) -> None:
        self._service.stop()
        self._runner.shutdown()


def run_listener(self_test: bool = False) -> int:
    configure_logging("listener.log")
    install_exception_logging()
    install_qt_logging()

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName("HotKey 监听器")
    app.setOrganizationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())

    if is_listener_running():
        logger.info("监听器已在运行")
        return 0

    listener = ListenerApp(app)  # noqa: F841 - 保持引用
    if self_test:
        QTimer.singleShot(400, listener.shutdown)
    return app.exec()
