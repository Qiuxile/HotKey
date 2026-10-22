"""主窗口：列表、编辑器、托盘与监听生命周期。"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizeGrip,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from hotkey.core import keymap, storage, validator
from hotkey.core.blocks import blocks_to_code
from hotkey.core.hotkey_service import HotkeyService
from hotkey.core.models import Block, HotKey, IssueLevel
from hotkey.core.program import render_program
from hotkey.core.runner import ScriptRunner
from hotkey.ui import theme as theme_module
from hotkey.ui.generated.ui_main_window import Ui_MainWindow
from hotkey.ui.hotkey_model import HotKeyFilterProxy, HotKeyTableModel
from hotkey.ui.recorder import HotKeyDialog
from hotkey.ui.widgets.title_bar import TitleBar

logger = logging.getLogger("HotKey.Window")

WINDOW_HEIGHT = 640
NARROW_WIDTH = 820
WIDE_WIDTH = 1240
PREVIEW_ID = "__preview__"


@dataclass
class Document:
    path: Path | None
    hotkeys: list[HotKey]
    title: str
    dirty: bool = False


class _Signals(QObject):
    """把 keyboard / runner 线程的回调安全地转发到主线程。"""

    triggered = Signal(str)
    started = Signal(str)
    finished = Signal(str, bool, str)


class MainWindow(QMainWindow):
    def __init__(
        self,
        config_path: Path | None = None,
        *,
        with_tray: bool = True,
        autostart: bool = False,
    ) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._documents: list[Document] = []
        self._active_index = -1
        self._model = HotKeyTableModel(parent=self)
        self._proxy = HotKeyFilterProxy(self)
        self._proxy.setSourceModel(self._model)
        self.ui.hotkeyTable.setModel(self._proxy)

        self._current_id: str | None = None
        self._listening = False
        self._quitting = False
        self._blocks_dirty = False
        self._tray: QSystemTrayIcon | None = None
        self._tray_start = None
        self._tray_stop = None

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(800)
        self._save_timer.timeout.connect(self._save_now)

        self._signals = _Signals(self)
        self._runner = ScriptRunner(
            on_started=self._signals.started.emit,
            on_finished=self._signals.finished.emit,
        )
        self._hotkey_service = HotkeyService(
            on_trigger=self._signals.triggered.emit,
            on_error=self._on_hotkey_error,
        )

        self._setup_chrome()
        self._configure_table()
        self._connect_signals()
        self._init_documents(config_path)
        self._init_theme()
        self._set_editor_visible(False)
        self._update_actions()

        if with_tray:
            self._setup_tray()

        if autostart and self._model.entries():
            self._start_listening()

    # ---------------------------------------------------------------- 窗口外观

    def _setup_chrome(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setMinimumSize(760, 520)

        self.title_bar = TitleBar(self)
        self.title_bar.theme_clicked.connect(self._toggle_theme)

        chrome = QWidget(self)
        layout = QVBoxLayout(chrome)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_bar)
        self.ui.menubar.setParent(chrome)
        self.ui.menubar.show()
        layout.addWidget(self.ui.menubar)
        self.setMenuWidget(chrome)

        self.ui.statusbar.addPermanentWidget(QSizeGrip(self), 0)
        self.resize(1120, WINDOW_HEIGHT)

    def _init_theme(self) -> None:
        dark = theme_module.current_theme() == "dark"
        self.ui.actionTheme.setChecked(dark)
        self.title_bar.set_theme_dark(dark)

    def _toggle_theme(self) -> None:
        name = "light" if theme_module.current_theme() == "dark" else "dark"
        theme_module.apply_theme(QApplication.instance(), name)
        dark = name == "dark"
        self.ui.actionTheme.setChecked(dark)
        self.title_bar.set_theme_dark(dark)
        self.statusBar().showMessage(
            "已切换到深色主题" if dark else "已切换到浅色主题", 3000
        )

    def changeEvent(self, event) -> None:  # noqa: N802
        if event.type() == QEvent.Type.WindowStateChange and hasattr(
            self, "title_bar"
        ):
            self.title_bar.set_maximized(self.isMaximized())
        super().changeEvent(event)

    # ---------------------------------------------------------------- 初始化

    def _configure_table(self) -> None:
        table = self.ui.hotkeyTable
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.setColumnWidth(2, 64)

    def _connect_signals(self) -> None:
        self.ui.actionQuit.triggered.connect(self._quit)
        self.ui.actionNew.triggered.connect(self._add_hotkey)
        self.ui.actionDelete.triggered.connect(self._delete_selected)
        self.ui.actionNewFile.triggered.connect(self._new_document)
        self.ui.actionImport.triggered.connect(self._open_document)
        self.ui.actionSave.triggered.connect(self._save_document)
        self.ui.actionExport.triggered.connect(self._save_document_as)
        self.ui.actionExportPython.triggered.connect(self._export_python)
        self.ui.actionTheme.triggered.connect(self._toggle_theme)
        self.ui.actionSearch.triggered.connect(self._focus_search)
        self.ui.actionToggleEditor.triggered.connect(self._toggle_editor)
        self.ui.actionStart.triggered.connect(self._start_listening)
        self.ui.actionStop.triggered.connect(self._stop_listening)

        self.ui.searchEdit.textChanged.connect(self._proxy.set_search_text)
        table = self.ui.hotkeyTable
        table.doubleClicked.connect(self._open_editor_from_index)
        table.customContextMenuRequested.connect(self._show_context_menu)

        self.ui.fileTabs.currentChanged.connect(self._on_tab_changed)
        self.ui.fileTabs.tabCloseRequested.connect(self._on_tab_close)
        self.ui.fileTabs.tabMoved.connect(self._on_tab_moved)
        self.ui.btnNewFile.clicked.connect(self._new_document)

        self.ui.btnSaveScript.clicked.connect(self._save_blocks)
        self.ui.btnExportPython.clicked.connect(self._export_python)
        self.ui.btnRunOnce.clicked.connect(self._run_once)
        self.ui.btnCloseEditor.clicked.connect(lambda: self._set_editor_visible(False))
        self.ui.btnCapturePos.clicked.connect(self._capture_coordinate)
        self.ui.btnCaptureColor.clicked.connect(self._capture_color)
        self.ui.btnScreenSize.clicked.connect(self._insert_screen_size)
        self.ui.blockEditor.changed.connect(self._on_blocks_changed)
        self._signals.triggered.connect(self._execute_hotkey)
        self._signals.started.connect(self._on_script_started)
        self._signals.finished.connect(self._on_script_finished)

    # ---------------------------------------------------------------- 多文件

    def _title_for(self, path: Path | None) -> str:
        return path.name if path is not None else "未命名"

    def _read_document(self, path: Path) -> tuple[list[HotKey], list[str]]:
        try:
            return storage.load_document(path)
        except storage.StorageError as exc:
            logger.error("读取配置失败: %s", exc)
            QTimer.singleShot(
                0,
                lambda: QMessageBox.warning(self, "配置读取失败", str(exc)),
            )
            return [], []

    def _init_documents(self, config_path: Path | None) -> None:
        path = (
            Path(config_path)
            if config_path is not None
            else storage.default_config_path()
        )
        entries, warnings = self._read_document(path)
        self._documents = [
            Document(path=path, hotkeys=entries, title=self._title_for(path))
        ]
        self._active_index = 0
        self._model.set_entries(entries)
        self._rebuild_tabs()
        self._update_window_title()

        if warnings:
            logger.info("配置提示: %s", "；".join(warnings))
        self.statusBar().showMessage(
            f"{self._title_for(path)} · {len(entries)} 个热键 · F5 启动监听"
            if entries
            else f"{self._title_for(path)} · 尚无热键，按 Ctrl+N 新建",
            8000,
        )

    def _active_document(self) -> Document | None:
        if 0 <= self._active_index < len(self._documents):
            return self._documents[self._active_index]
        return None

    def _commit_active(self) -> None:
        document = self._active_document()
        if document is not None:
            document.hotkeys = self._model.entries()

    def _tab_text(self, document: Document) -> str:
        return document.title + (" *" if document.dirty else "")

    def _rebuild_tabs(self) -> None:
        bar = self.ui.fileTabs
        bar.blockSignals(True)
        while bar.count():
            bar.removeTab(0)
        for index, document in enumerate(self._documents):
            bar.addTab(self._tab_text(document))
            bar.setTabToolTip(
                index, str(document.path) if document.path else "尚未保存"
            )
        if self._documents:
            self._active_index = max(
                0, min(self._active_index, len(self._documents) - 1)
            )
            bar.setCurrentIndex(self._active_index)
        bar.blockSignals(False)

    def _update_tab(self, index: int) -> None:
        if 0 <= index < len(self._documents):
            self.ui.fileTabs.setTabText(index, self._tab_text(self._documents[index]))

    def _update_window_title(self) -> None:
        document = self._active_document()
        if document is None:
            return
        name = document.title + (" *" if document.dirty else "")
        state = "监听中" if self._listening else ""
        suffix = f"（{state}）" if state else ""
        self.setWindowTitle(f"{name} - HotKey{suffix}")
        if hasattr(self, "title_bar"):
            self.title_bar.set_title(f"HotKey · {name}{suffix}")

    def _on_tab_changed(self, index: int) -> None:
        if index < 0 or index == self._active_index:
            return
        self._commit_active()
        self._active_index = index
        document = self._documents[index]
        self._model.set_entries(document.hotkeys)
        self._current_id = None
        self._blocks_dirty = False
        self._set_editor_visible(False)
        self._update_window_title()
        self.statusBar().showMessage(
            f"{document.title} · {len(document.hotkeys)} 个热键", 4000
        )

    def _on_tab_moved(self, from_index: int, to_index: int) -> None:
        document = self._documents.pop(from_index)
        self._documents.insert(to_index, document)
        if self._active_index == from_index:
            self._active_index = to_index
        elif from_index < self._active_index <= to_index:
            self._active_index -= 1
        elif to_index <= self._active_index < from_index:
            self._active_index += 1

    def _on_tab_close(self, index: int) -> None:
        self._close_document(index)

    def _new_document(self) -> None:
        self._commit_active()
        self._documents.append(
            Document(path=None, hotkeys=[], title="未命名", dirty=False)
        )
        self._rebuild_tabs()
        self.ui.fileTabs.setCurrentIndex(len(self._documents) - 1)
        self.statusBar().showMessage("新建文件 · 保存时会询问路径", 4000)

    def _open_document(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "打开热键文件",
            str(self._default_dir()),
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        if path:
            self._open_document_path(Path(path))

    def _open_document_path(self, path: Path) -> None:
        path = Path(path).resolve()
        for index, document in enumerate(self._documents):
            if document.path is not None and document.path.resolve() == path:
                self.ui.fileTabs.setCurrentIndex(index)
                return

        entries, warnings = self._read_document(path)
        self._commit_active()
        self._documents.append(
            Document(path=path, hotkeys=entries, title=self._title_for(path))
        )
        self._rebuild_tabs()
        self.ui.fileTabs.setCurrentIndex(len(self._documents) - 1)

        if warnings:
            shown = "\n".join(warnings[:8])
            if len(warnings) > 8:
                shown += f"\n… 其余 {len(warnings) - 8} 条略"
            QMessageBox.warning(self, "打开完成，但有以下提示", shown)

    def _save_document(self) -> None:
        self._save_document_index(self._active_index)

    def _save_document_as(self) -> None:
        self._save_document_index(self._active_index, force_dialog=True)

    def _save_document_index(self, index: int, force_dialog: bool = False) -> bool:
        if not 0 <= index < len(self._documents):
            return False
        if index == self._active_index:
            self._commit_active()

        document = self._documents[index]
        target = document.path
        if target is None or force_dialog:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "保存热键文件",
                str(document.path or (self._default_dir() / "hotkeys.json")),
                "JSON 文件 (*.json);;所有文件 (*)",
            )
            if not path:
                return False
            target = Path(path)

        try:
            storage.save(target, document.hotkeys)
        except storage.StorageError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return False

        document.path = target
        document.title = self._title_for(target)
        document.dirty = False
        self._rebuild_tabs()
        self._update_window_title()
        self.statusBar().showMessage(f"已保存 {target}", 5000)
        return True

    def _close_document(self, index: int) -> None:
        if not 0 <= index < len(self._documents):
            return
        if index == self._active_index:
            self._commit_active()

        document = self._documents[index]
        if document.dirty:
            answer = QMessageBox.question(
                self,
                "关闭文件",
                f"{document.title} 有未保存的修改，要保存吗？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return
            if answer == QMessageBox.StandardButton.Save:
                if not self._save_document_index(index):
                    return

        self._documents.pop(index)
        if not self._documents:
            self._documents.append(
                Document(path=None, hotkeys=[], title="未命名", dirty=False)
            )
            self._active_index = 0
        elif index < self._active_index:
            self._active_index -= 1
        elif index == self._active_index:
            self._active_index = min(index, len(self._documents) - 1)

        self._rebuild_tabs()
        self._model.set_entries(
            self._documents[self._active_index].hotkeys
            if self._documents
            else []
        )
        self._current_id = None
        self._set_editor_visible(False)
        self._update_window_title()

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("系统托盘不可用")
            return

        menu = QMenu(self)
        show_action = menu.addAction("显示主窗口")
        show_action.triggered.connect(self._show_window)
        self._tray_start = menu.addAction("开始监听")
        self._tray_start.triggered.connect(self._start_listening)
        self._tray_stop = menu.addAction("停止监听")
        self._tray_stop.triggered.connect(self._stop_listening)
        menu.addSeparator()
        quit_action = menu.addAction("退出")
        quit_action.triggered.connect(self._quit)

        self._tray = QSystemTrayIcon(self._make_icon(), self)
        self._tray.setContextMenu(menu)
        self._tray.setToolTip("HotKey · 未监听")
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _make_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#4a8fe7"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(2, 2, 60, 60, 14, 14)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "HK")
        painter.end()
        return QIcon(pixmap)

    # ---------------------------------------------------------------- 列表操作

    def _selected_source_row(self) -> int | None:
        rows = self.ui.hotkeyTable.selectionModel().selectedRows()
        if not rows:
            return None
        source = self._proxy.mapToSource(rows[0])
        return source.row() if source.isValid() else None

    def _show_context_menu(self, position) -> None:
        table = self.ui.hotkeyTable
        index = table.indexAt(position)
        menu = QMenu(self)

        if not index.isValid():
            menu.addAction("新建热键", self._add_hotkey)
            menu.exec(table.viewport().mapToGlobal(position))
            return

        table.selectRow(index.row())
        row = self._selected_source_row()
        if row is None:
            return
        entry = self._model.entry(row)

        menu.addAction("编辑脚本", lambda: self._open_editor_for_id(entry.id))
        menu.addAction("修改热键…", lambda: self._modify_hotkey(row))
        menu.addAction(
            "停用" if entry.enabled else "启用",
            lambda: self._toggle_hotkey(row),
        )
        menu.addSeparator()
        menu.addAction("删除", lambda: self._delete_row(row))
        menu.addSeparator()
        menu.addAction("新建热键", self._add_hotkey)
        menu.exec(table.viewport().mapToGlobal(position))

    def _add_hotkey(self) -> None:
        dialog = HotKeyDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        key = dialog.hotkey_key()
        if self._key_exists(key):
            QMessageBox.warning(self, "热键重复", f"{key} 已经被其他条目使用。")
            return

        entry = HotKey(
            key=key,
            description=dialog.hotkey_description(),
            script="",
        )
        self._model.add(entry)
        self._schedule_save()
        self._reload_service()
        self._open_editor_for_id(entry.id)

    def _modify_hotkey(self, row: int) -> None:
        entry = self._model.entry(row)
        dialog = HotKeyDialog(self, key=entry.key, description=entry.description)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        key = dialog.hotkey_key()
        if self._key_exists(key, ignore_id=entry.id):
            QMessageBox.warning(self, "热键重复", f"{key} 已经被其他条目使用。")
            return

        entry.key = key
        entry.description = dialog.hotkey_description()
        self._model.touch(row)
        if self._current_id == entry.id:
            self.ui.lblEditing.setText(
                f"操作编辑 · {keymap.keyboard_to_qt(entry.key)}"
            )
        self._schedule_save()
        self._reload_service()

    def _toggle_hotkey(self, row: int) -> None:
        self._model.toggle(row)
        self._schedule_save()
        self._reload_service()

    def _delete_selected(self) -> None:
        row = self._selected_source_row()
        if row is not None:
            self._delete_row(row)

    def _delete_row(self, row: int) -> None:
        entry = self._model.entry(row)
        answer = QMessageBox.question(
            self,
            "删除热键",
            f"确定删除 {keymap.keyboard_to_qt(entry.key)}"
            + (f"（{entry.description}）" if entry.description else "")
            + " 吗？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._model.remove(row)
        if self._current_id == entry.id:
            self._current_id = None
            self._set_editor_visible(False)
        self._schedule_save()
        self._reload_service()

    def _key_exists(self, key: str, ignore_id: str | None = None) -> bool:
        needle = keymap.normalize_key(key)
        for entry in self._model.entries():
            if entry.id == ignore_id:
                continue
            if keymap.normalize_key(entry.key) == needle:
                return True
        return False

    # ---------------------------------------------------------------- 编辑器

    def _open_editor_from_index(self, index) -> None:
        source = self._proxy.mapToSource(index)
        if not source.isValid():
            return
        self._open_editor_for_id(self._model.entry(source.row()).id)

    def _open_editor_for_id(self, hotkey_id: str) -> None:
        row = self._model.row_of(hotkey_id)
        if row is None:
            return
        entry = self._model.entry(row)
        self._current_id = hotkey_id

        blocks = entry.blocks
        if not blocks and entry.script.strip():
            blocks = [Block(kind="empty", text=entry.script)]

        self.ui.lblEditing.setText(
            f"操作编辑 · {keymap.keyboard_to_qt(entry.key)}（参数直接填在积木里）"
        )
        self.ui.blockEditor.load_blocks(blocks)
        self._blocks_dirty = False
        self._set_editor_visible(True)
        self.ui.blockEditor.setFocus()

    def _toggle_editor(self) -> None:
        self._set_editor_visible(self.ui.editorPanel.isHidden())

    def _set_editor_visible(self, visible: bool) -> None:
        self.ui.editorPanel.setVisible(visible)
        self.ui.actionToggleEditor.setChecked(visible)
        if visible:
            self.ui.centralSplitter.setSizes([NARROW_WIDTH, 750])
            self.resize(WIDE_WIDTH, WINDOW_HEIGHT)
        else:
            self._current_id = None
            self._blocks_dirty = False
            self.resize(NARROW_WIDTH, WINDOW_HEIGHT)

    def _on_blocks_changed(self) -> None:
        if not self._blocks_dirty:
            self.statusBar().showMessage("积木已修改，点「保存」写入热键", 3000)
            self._blocks_dirty = True

    def _save_blocks(self) -> None:
        if self._current_id is None:
            return
        row = self._model.row_of(self._current_id)
        if row is None:
            return

        blocks = self.ui.blockEditor.blocks()
        script = blocks_to_code(blocks)
        issues = validator.validate(script)
        errors = [issue for issue in issues if issue.level is IssueLevel.ERROR]
        if errors:
            detail = "\n".join(str(issue) for issue in errors[:8])
            QMessageBox.critical(
                self,
                "无法保存",
                "积木组合出的脚本有问题（通常是参数没填）：\n\n" + detail,
            )
            return

        entry = self._model.entry(row)
        entry.blocks = blocks
        entry.script = script
        self._model.touch(row)
        self._blocks_dirty = False
        self._schedule_save()
        self._reload_service()
        self.statusBar().showMessage(f"已保存 {len(blocks)} 个积木", 3000)

    def _run_once(self) -> None:
        script = blocks_to_code(self.ui.blockEditor.blocks())
        if not script.strip():
            self.statusBar().showMessage("积木栏是空的", 3000)
            return
        self._runner.submit(PREVIEW_ID, script)
        self.statusBar().showMessage("试运行中…", 3000)

    def _copy_value(self, text: str, label: str) -> None:
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(
            f"{label} {text} 已复制；选中积木按空格编辑，再粘贴进去",
            8000,
        )

    def _capture_coordinate(self) -> None:
        self.statusBar().showMessage("3 秒后捕获鼠标坐标，请把鼠标移到目标位置…", 3500)
        QTimer.singleShot(3000, self._insert_mouse_position)

    def _insert_mouse_position(self) -> None:
        try:
            import pyautogui

            x, y = pyautogui.position()
        except Exception as exc:  # noqa: BLE001
            logger.warning("捕获坐标失败: %s", exc)
            self.statusBar().showMessage("捕获失败：需要安装 pyautogui", 5000)
            return
        self._copy_value(f"{x}, {y}", "坐标")

    def _capture_color(self) -> None:
        self.statusBar().showMessage("3 秒后捕获像素颜色，请把鼠标移到目标位置…", 3500)
        QTimer.singleShot(3000, self._insert_pixel_color)

    def _insert_pixel_color(self) -> None:
        try:
            import pyautogui

            x, y = pyautogui.position()
            r, g, b = pyautogui.pixel(x, y)
        except Exception as exc:  # noqa: BLE001
            logger.warning("捕获颜色失败: %s", exc)
            self.statusBar().showMessage("捕获失败：需要安装 pyautogui", 5000)
            return
        self._copy_value(f"({r}, {g}, {b})", "颜色")

    def _insert_screen_size(self) -> None:
        try:
            import pyautogui

            width, height = pyautogui.size()
        except Exception:  # noqa: BLE001
            width, height = 1920, 1080
        self._copy_value(f"{width}, {height}", "屏幕尺寸")

    # ---------------------------------------------------------------- 监听

    def _executable_entries(self) -> list[HotKey]:
        return [
            entry
            for entry in self._model.entries()
            if entry.enabled and entry.script.strip()
        ]

    def _start_listening(self) -> None:
        entries = self._executable_entries()
        if not entries:
            QMessageBox.information(
                self,
                "没有可运行的热键",
                "请先启用热键并在编辑器里保存脚本。",
            )
            return

        try:
            self._hotkey_service.start(entries)
        except Exception as exc:  # noqa: BLE001
            logger.exception("启动监听失败")
            QMessageBox.critical(self, "启动失败", str(exc))
            return

        self._set_listening(True)
        self.statusBar().showMessage(f"监听已启动，共 {len(entries)} 个热键", 5000)

    def _stop_listening(self) -> None:
        self._hotkey_service.stop()
        self._set_listening(False)
        self.statusBar().showMessage("监听已停止", 4000)

    def _reload_service(self) -> None:
        if not self._listening:
            return
        try:
            self._hotkey_service.reload(self._executable_entries())
        except Exception:  # noqa: BLE001
            logger.exception("重新注册热键失败")
            self._set_listening(False)
            QMessageBox.warning(
                self,
                "监听已停止",
                "热键重新注册失败，请检查组合键是否有效。",
            )

    def _set_listening(self, listening: bool) -> None:
        self._listening = listening
        self._update_actions()
        state = "监听中" if listening else "已停止"
        self._update_window_title()
        if self._tray is not None:
            self._tray.setToolTip(f"HotKey · {state}")

    def _update_actions(self) -> None:
        self.ui.actionStart.setEnabled(not self._listening)
        self.ui.actionStop.setEnabled(self._listening)
        if self._tray_start is not None:
            self._tray_start.setEnabled(not self._listening)
        if self._tray_stop is not None:
            self._tray_stop.setEnabled(self._listening)

    def _execute_hotkey(self, hotkey_id: str) -> None:
        row = self._model.row_of(hotkey_id)
        if row is None:
            return
        entry = self._model.entry(row)
        if entry.script.strip():
            self._runner.submit(entry.id, entry.script)

    def _on_script_started(self, hotkey_id: str) -> None:
        if hotkey_id != PREVIEW_ID:
            self.statusBar().showMessage("正在执行热键脚本…")

    def _on_script_finished(self, hotkey_id: str, ok: bool, message: str) -> None:
        if hotkey_id == PREVIEW_ID:
            if ok:
                self.statusBar().showMessage("试运行完成", 4000)
            else:
                QMessageBox.warning(self, "试运行失败", message or "脚本执行失败")
            return

        row = self._model.row_of(hotkey_id)
        label = (
            keymap.keyboard_to_qt(self._model.entry(row).key)
            if row is not None
            else hotkey_id
        )
        if ok:
            self.statusBar().showMessage(f"{label} 执行完成", 3000)
        else:
            logger.error("热键 %s 执行失败: %s", label, message)
            self.statusBar().showMessage(f"{label} 执行失败：{message}", 8000)
            if self._tray is not None:
                self._tray.showMessage(
                    "热键执行失败",
                    f"{label}\n{message}",
                    QSystemTrayIcon.MessageIcon.Warning,
                    4000,
                )

    def _on_hotkey_error(self, key: str, message: str) -> None:
        logger.error("热键 %s 注册失败: %s", key, message)
        self.statusBar().showMessage(f"热键 {key} 注册失败：{message}", 8000)

    # ---------------------------------------------------------------- 文件

    def _default_dir(self) -> Path:
        local = Path.cwd() / "jsons"
        return local if local.exists() else Path.home()

    def _export_python(self) -> None:
        row = self._model.row_of(self._current_id) if self._current_id else None
        if row is None:
            row = self._selected_source_row()
        if row is None:
            QMessageBox.information(
                self, "导出 Python", "请先选中一个热键，或双击打开它的积木。"
            )
            return

        entry = self._model.entry(row)
        blocks = (
            self.ui.blockEditor.blocks()
            if self._current_id == entry.id
            else entry.blocks
        )
        if not blocks:
            QMessageBox.information(self, "导出 Python", "这个热键还没有积木。")
            return

        source = render_program(blocks)
        try:
            compile(source, "<export>", "exec")
        except SyntaxError as exc:
            QMessageBox.critical(
                self,
                "无法生成",
                "生成的脚本有语法错误（通常是变量名或参数没填完整）：\n"
                f"第 {exc.lineno} 行：{exc.msg}",
            )
            return

        name = re.sub(r"[^0-9A-Za-z_\-]+", "_", entry.key).strip("_") or "hotkey"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 Python 文件",
            str(self._default_dir() / f"{name}.py"),
            "Python 文件 (*.py);;所有文件 (*)",
        )
        if not path:
            return

        target = Path(path)
        try:
            target.write_text(source, encoding="utf-8", newline="\n")
        except OSError as exc:
            QMessageBox.critical(self, "导出失败", str(exc))
            return

        self.statusBar().showMessage(f"已生成 {target}", 8000)
        QMessageBox.information(
            self,
            "已生成",
            f"已生成 {target.name}。\n\n可以直接运行：\npython \"{target}\"",
        )

    def _save_now(self) -> None:
        self._save_timer.stop()
        if self._active_index < 0:
            return
        self._commit_active()
        document = self._active_document()
        if document is None:
            return
        if document.path is None:
            self._update_tab(self._active_index)
            return

        try:
            storage.save(document.path, document.hotkeys)
        except storage.StorageError as exc:
            logger.error("保存配置失败: %s", exc)
            self.statusBar().showMessage(f"保存失败：{exc}", 8000)
            return

        document.dirty = False
        self._update_tab(self._active_index)
        self._update_window_title()
        self.statusBar().showMessage("已自动保存", 1500)

    def _schedule_save(self) -> None:
        document = self._active_document()
        if document is None:
            return
        document.dirty = True
        self._update_tab(self._active_index)
        self._update_window_title()
        self._save_timer.start()

    # ---------------------------------------------------------------- 托盘/退出

    def _focus_search(self) -> None:
        self.ui.searchEdit.setFocus()
        self.ui.searchEdit.selectAll()

    def _on_tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._show_window()

    def _show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._quitting:
            super().closeEvent(event)
            return

        if self._tray is not None:
            event.ignore()
            self._save_now()
            self.hide()
            self._tray.showMessage(
                "HotKey",
                "已最小化到托盘，热键继续运行。右键托盘图标可退出。",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            return

        self._save_now()
        self._hotkey_service.stop()
        self._runner.shutdown()
        event.accept()

    def _quit(self) -> None:
        for index, document in enumerate(list(self._documents)):
            if not document.dirty:
                continue
            if document.path is None:
                answer = QMessageBox.question(
                    self,
                    "未保存的文件",
                    f"{document.title} 还没有保存，要保存吗？",
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel,
                )
                if answer == QMessageBox.StandardButton.Cancel:
                    return
                if answer == QMessageBox.StandardButton.Discard:
                    continue
            if not self._save_document_index(index):
                return

        self._quitting = True
        self._hotkey_service.stop()
        self._runner.shutdown()
        if self._tray is not None:
            self._tray.hide()
        QApplication.quit()
