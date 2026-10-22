"""主窗口：脚本库、编辑标签、热键监听与托盘。"""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
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
from hotkey.core.library import (
    ScriptLibrary,
    default_script_dir,
    safe_stem,
)
from hotkey.core.models import Block, HotKey, IssueLevel, new_id
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
SETTINGS_OPEN_TABS = "open_scripts"
SETTINGS_ACTIVE_TAB = "active_script"


@dataclass
class EditorTab:
    hotkey_id: str
    blocks: list[Block] = field(default_factory=list)
    dirty: bool = False


class _Signals(QObject):
    """把 keyboard / runner 线程的回调安全地转发到主线程。"""

    triggered = Signal(str)
    started = Signal(str)
    finished = Signal(str, bool, str)


class MainWindow(QMainWindow):
    def __init__(
        self,
        library_dir: Path | None = None,
        *,
        with_tray: bool = True,
        autostart: bool = False,
    ) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # QTabBar 在部分布局里会被压成 0 高，强制一个可读高度
        self.ui.editorTabs.setMinimumHeight(28)
        self.ui.editorTabs.setExpanding(False)
        self.ui.editorTabs.setElideMode(Qt.TextElideMode.ElideRight)

        self._library = ScriptLibrary(
            Path(library_dir) if library_dir is not None else default_script_dir()
        )
        self._editor_tabs: list[EditorTab] = []
        self._active_tab = -1
        self._current_id: str | None = None

        self._model = HotKeyTableModel(parent=self)
        self._proxy = HotKeyFilterProxy(self)
        self._proxy.setSourceModel(self._model)
        self.ui.hotkeyTable.setModel(self._proxy)

        self._listening = False
        self._quitting = False
        self._blocks_dirty = False
        self._tray: QSystemTrayIcon | None = None
        self._tray_start = None
        self._tray_stop = None

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._save_all_metadata)

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
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
        self._configure_table()
        self._connect_signals()
        self._load_library()
        self._init_theme()
        self._set_editor_visible(False)
        self._update_actions()

        if with_tray:
            self._setup_tray()

        self._restore_tabs()

        if autostart:
            self._start_listening()

    # ---------------------------------------------------------------- 外观

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
        self.setMenuWidget(chrome)
        self.title_bar.attach_menu(self.ui.menubar)

        self.ui.statusbar.addPermanentWidget(QSizeGrip(self), 0)
        self.resize(1120, WINDOW_HEIGHT)

    # ---------------------------------------------------------------- 窗口缩放

    def _edges_at(self, pos: QPoint) -> Qt.Edge:
        if self.isMaximized() or self.isFullScreen():
            return Qt.Edge(0)
        border = 6
        edges = Qt.Edge(0)
        if pos.x() < border:
            edges |= Qt.Edge.LeftEdge
        elif pos.x() >= self.width() - border:
            edges |= Qt.Edge.RightEdge
        if pos.y() < border:
            edges |= Qt.Edge.TopEdge
        elif pos.y() >= self.height() - border:
            edges |= Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def _cursor_for_edges(edges: Qt.Edge) -> Qt.CursorShape:
        left = bool(edges & Qt.Edge.LeftEdge)
        right = bool(edges & Qt.Edge.RightEdge)
        top = bool(edges & Qt.Edge.TopEdge)
        bottom = bool(edges & Qt.Edge.BottomEdge)
        if (left and top) or (right and bottom):
            return Qt.CursorShape.SizeFDiagCursor
        if (right and top) or (left and bottom):
            return Qt.CursorShape.SizeBDiagCursor
        if left or right:
            return Qt.CursorShape.SizeHorCursor
        if top or bottom:
            return Qt.CursorShape.SizeVerCursor
        return Qt.CursorShape.ArrowCursor

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if isinstance(watched, QWidget) and watched.window() is self:
            if (
                event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
            ):
                edges = self._edges_at(
                    watched.mapTo(self, event.position().toPoint())
                )
                if edges:
                    handle = self.windowHandle()
                    if handle is not None and handle.startSystemResize(edges):
                        return True
            elif event.type() == QEvent.Type.MouseMove:
                edges = self._edges_at(
                    watched.mapTo(self, event.position().toPoint())
                )
                if edges:
                    self.setCursor(self._cursor_for_edges(edges))
                else:
                    self.unsetCursor()
        return super().eventFilter(watched, event)

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
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.setColumnWidth(2, 64)

    def _connect_signals(self) -> None:
        self.ui.actionQuit.triggered.connect(self._quit)
        self.ui.actionNew.triggered.connect(self._new_script)
        self.ui.actionDelete.triggered.connect(self._delete_selected)
        self.ui.actionImport.triggered.connect(self._import_script)
        self.ui.actionSave.triggered.connect(self._save_current_tab)
        self.ui.actionSetHotkey.triggered.connect(self._set_hotkey)
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

        self.ui.editorTabs.currentChanged.connect(self._on_tab_changed)
        self.ui.editorTabs.tabCloseRequested.connect(self._close_tab)
        self.ui.editorTabs.tabMoved.connect(self._on_tab_moved)

        self.ui.btnNewScript.clicked.connect(self._new_script)
        self.ui.btnSaveScript.clicked.connect(self._save_current_tab)
        self.ui.btnRunOnce.clicked.connect(self._run_script)
        self.ui.btnExportPython.clicked.connect(self._export_python)
        self.ui.btnCloseEditor.clicked.connect(lambda: self._set_editor_visible(False))
        self.ui.btnCapturePos.clicked.connect(self._capture_coordinate)
        self.ui.btnCaptureColor.clicked.connect(self._capture_color)
        self.ui.btnScreenSize.clicked.connect(self._insert_screen_size)
        self.ui.blockEditor.changed.connect(self._on_blocks_changed)

        self._signals.triggered.connect(self._execute_hotkey)
        self._signals.started.connect(self._on_script_started)
        self._signals.finished.connect(self._on_script_finished)

    def _load_library(self) -> None:
        scripts = self._library.load()
        self._model.set_entries(scripts)
        warnings = self._library.warnings
        if warnings:
            logger.info("脚本库提示: %s", "；".join(warnings))
            self.statusBar().showMessage(warnings[0], 10000)
        else:
            self.statusBar().showMessage(
                f"脚本库：{self._library.directory} · {len(scripts)} 个脚本",
                8000,
            )
        self._update_window_title()

    # ---------------------------------------------------------------- 脚本库

    def _selected_source_row(self) -> int | None:
        rows = self.ui.hotkeyTable.selectionModel().selectedRows()
        if not rows:
            return None
        source = self._proxy.mapToSource(rows[0])
        return source.row() if source.isValid() else None

    def _active_entry(self) -> HotKey | None:
        if self._current_id is None:
            return None
        row = self._model.row_of(self._current_id)
        return self._model.entry(row) if row is not None else None

    def _new_script(self) -> None:
        default = self._library.directory / "新脚本.hk"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "新建脚本",
            str(default),
            "HotKey 脚本 (*.hk);;所有文件 (*)",
        )
        if not path:
            return

        target = Path(path)
        if self._library.directory.resolve() != target.resolve().parent:
            QMessageBox.warning(
                self,
                "路径不支持",
                f"脚本必须直接保存在脚本目录里：\n{self._library.directory}",
            )
            return
        if target.suffix.lower() != ".hk":
            target = target.with_suffix(".hk")

        for entry in self._model.entries():
            if entry.path is not None and entry.path.resolve() == target.resolve():
                QMessageBox.warning(
                    self,
                    "脚本已存在",
                    f"「{entry.name}」已经使用了这个文件，请换一个名字。",
                )
                return

        script = HotKey(
            key="",
            name=target.stem,
            path=target,
            blocks=[],
        )
        try:
            self._library.save(script)
        except storage.StorageError as exc:
            QMessageBox.critical(self, "新建失败", str(exc))
            return

        self._model.add(script)
        self._open_editor_for_id(script.id)
        self.statusBar().showMessage(f"已新建脚本 {target.name}", 5000)

    def _import_script(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入脚本",
            str(self._library.directory),
            "HotKey 脚本 (*.hk *.json);;所有文件 (*)",
        )
        if not path:
            return

        try:
            script = self._library.import_copy(Path(path))
        except storage.StorageError as exc:
            QMessageBox.critical(self, "导入失败", str(exc))
            return

        if self._model.row_of(script.id) is not None:
            script.id = new_id()
            self._library.save(script)
        self._model.add(script)
        self._open_editor_for_id(script.id)
        self.statusBar().showMessage(f"已导入脚本 {script.name}", 5000)

    def _delete_selected(self) -> None:
        row = self._selected_source_row()
        if row is None:
            return
        self._delete_script(row)

    def _delete_script(self, row: int) -> None:
        entry = self._model.entry(row)
        answer = QMessageBox.question(
            self,
            "删除脚本",
            f"确定删除「{entry.name or entry.key}」吗？\n磁盘上的 {entry.path.name if entry.path else '脚本文件'} 也会被删除。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self._close_tab_for_id(entry.id, ask=False)
        self._library.delete(entry)
        self._model.remove(row)
        self._persist_tabs()
        self._update_window_title()
        self.statusBar().showMessage(f"已删除 {entry.name}", 4000)

    def _toggle_script(self, row: int) -> None:
        self._model.toggle(row)
        entry = self._model.entry(row)
        self._save_metadata(entry)
        self._reload_service()

    def _set_hotkey(self) -> None:
        row = self._selected_source_row()
        if row is None and self._current_id is not None:
            row = self._model.row_of(self._current_id)
        if row is None:
            QMessageBox.information(self, "设置热键", "请先选中一个脚本。")
            return
        self._edit_hotkey(row)

    def _edit_hotkey(self, row: int) -> None:
        entry = self._model.entry(row)
        dialog = HotKeyDialog(self, key=entry.key, description=entry.description)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        key = dialog.hotkey_key()
        for index, other in enumerate(self._model.entries()):
            if index == row or not other.key:
                continue
            if keymap.normalize_key(other.key) == keymap.normalize_key(key):
                QMessageBox.warning(
                    self, "热键重复", f"{key} 已经被「{other.name}」使用。"
                )
                return

        entry.key = key
        entry.description = dialog.hotkey_description()
        self._model.touch(row)
        self._save_metadata(entry)
        self._refresh_tab_labels()
        self._reload_service()

    def _clear_hotkey(self, row: int) -> None:
        entry = self._model.entry(row)
        entry.key = ""
        self._model.touch(row)
        self._save_metadata(entry)
        self._refresh_tab_labels()
        self._reload_service()
        self.statusBar().showMessage("已清除热键，脚本仍可手动运行/导出", 5000)

    def _show_context_menu(self, position) -> None:
        table = self.ui.hotkeyTable
        index = table.indexAt(position)
        menu = QMenu(self)

        if not index.isValid():
            menu.addAction("新建脚本", self._new_script)
            menu.exec(table.viewport().mapToGlobal(position))
            return

        table.selectRow(index.row())
        row = self._selected_source_row()
        if row is None:
            return
        entry = self._model.entry(row)

        menu.addAction("编辑脚本", lambda: self._open_editor_for_id(entry.id))
        menu.addAction("运行一次", lambda: self._run_entry(entry.id))
        menu.addAction("设置热键…", lambda: self._edit_hotkey(row))
        if entry.key:
            menu.addAction("清除热键", lambda: self._clear_hotkey(row))
        menu.addAction(
            "停用" if entry.enabled else "启用", lambda: self._toggle_script(row)
        )
        menu.addSeparator()
        menu.addAction("删除", lambda: self._delete_script(row))
        menu.addSeparator()
        menu.addAction("新建脚本", self._new_script)
        menu.exec(table.viewport().mapToGlobal(position))

    # ---------------------------------------------------------------- 编辑标签

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

        existing = self._tab_index(hotkey_id)
        if existing < 0:
            blocks = deepcopy(entry.blocks)
            if not blocks and entry.script.strip():
                blocks = [Block(kind="empty", text=entry.script)]
            self._editor_tabs.append(
                EditorTab(hotkey_id=hotkey_id, blocks=blocks, dirty=False)
            )
            existing = len(self._editor_tabs) - 1
            self._rebuild_tabs(existing)

        self._set_editor_visible(True)
        self.ui.editorTabs.setCurrentIndex(existing)
        self._activate_tab(existing)

    def _tab_index(self, hotkey_id: str) -> int:
        for index, tab in enumerate(self._editor_tabs):
            if tab.hotkey_id == hotkey_id:
                return index
        return -1

    def _tab_label(self, tab: EditorTab) -> str:
        row = self._model.row_of(tab.hotkey_id)
        if row is None:
            return "（已删除）"
        entry = self._model.entry(row)
        name = entry.name or entry.key or "脚本"
        return name + (" *" if tab.dirty else "")

    def _rebuild_tabs(self, current: int) -> None:
        bar = self.ui.editorTabs
        bar.blockSignals(True)
        while bar.count():
            bar.removeTab(0)
        for index, tab in enumerate(self._editor_tabs):
            bar.addTab(self._tab_label(tab))
        if self._editor_tabs:
            bar.setCurrentIndex(max(0, min(current, len(self._editor_tabs) - 1)))
        bar.blockSignals(False)

    def _activate_tab(self, index: int) -> None:
        if not 0 <= index < len(self._editor_tabs):
            return
        tab = self._editor_tabs[index]
        row = self._model.row_of(tab.hotkey_id)
        if row is None:
            return
        entry = self._model.entry(row)

        self._active_tab = index
        self._current_id = entry.id
        self._blocks_dirty = tab.dirty
        self.ui.blockEditor.load_blocks(tab.blocks)
        hotkey_text = (
            keymap.keyboard_to_qt(entry.key) if entry.key else "无热键"
        )
        self.ui.lblEditing.setText(
            f"{entry.name} · 热键：{hotkey_text} · 参数直接填在积木里"
        )
        self.ui.editorTabs.setCurrentIndex(index)
        self._update_window_title()
        self._persist_tabs()

    def _on_tab_changed(self, index: int) -> None:
        if index < 0 or index == self._active_tab:
            return
        if self._active_tab >= 0:
            self._commit_tab()
        self._activate_tab(index)

    def _on_tab_moved(self, from_index: int, to_index: int) -> None:
        tab = self._editor_tabs.pop(from_index)
        self._editor_tabs.insert(to_index, tab)
        if self._active_tab == from_index:
            self._active_tab = to_index
        elif from_index < self._active_tab <= to_index:
            self._active_tab -= 1
        elif to_index <= self._active_tab < from_index:
            self._active_tab += 1
        self._persist_tabs()

    def _on_blocks_changed(self) -> None:
        tab = self._active_tab_object()
        if tab is None:
            return
        tab.dirty = True
        self._blocks_dirty = True
        self.ui.editorTabs.setTabText(self._active_tab, self._tab_label(tab))
        self.statusBar().showMessage("积木已修改，点「保存」写入脚本文件", 3000)

    def _active_tab_object(self) -> EditorTab | None:
        if 0 <= self._active_tab < len(self._editor_tabs):
            return self._editor_tabs[self._active_tab]
        return None

    def _commit_tab(self) -> None:
        tab = self._active_tab_object()
        if tab is not None:
            tab.blocks = self.ui.blockEditor.blocks()

    def _save_current_tab(self) -> None:
        self._save_tab(self._active_tab)

    def _save_tab(self, index: int) -> bool:
        if not 0 <= index < len(self._editor_tabs):
            return False
        tab = self._editor_tabs[index]
        if index == self._active_tab:
            tab.blocks = self.ui.blockEditor.blocks()

        row = self._model.row_of(tab.hotkey_id)
        if row is None:
            return False
        entry = self._model.entry(row)

        script = blocks_to_code(tab.blocks)
        issues = validator.validate(script)
        errors = [issue for issue in issues if issue.level is IssueLevel.ERROR]
        if errors:
            detail = "\n".join(str(issue) for issue in errors[:8])
            QMessageBox.critical(
                self,
                "无法保存",
                "积木组合出的脚本有问题（通常是参数没填）：\n\n" + detail,
            )
            return False

        entry.blocks = tab.blocks
        entry.script = script
        try:
            self._library.save(entry)
        except storage.StorageError as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return False

        self._model.touch(row)
        tab.dirty = False
        if index == self._active_tab:
            self._blocks_dirty = False
        self.ui.editorTabs.setTabText(index, self._tab_label(tab))
        self._reload_service()
        self.statusBar().showMessage(f"已保存 {entry.path.name if entry.path else entry.name}", 4000)
        return True

    def _close_tab(self, index: int) -> None:
        if not 0 <= index < len(self._editor_tabs):
            return
        was_active = index == self._active_tab
        if was_active:
            self._commit_tab()
        tab = self._editor_tabs[index]

        if tab.dirty:
            answer = QMessageBox.question(
                self,
                "关闭标签",
                f"「{self._tab_label(tab).rstrip(' *')}」有未保存的修改，要保存吗？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return
            if answer == QMessageBox.StandardButton.Save and not self._save_tab(index):
                return

        self._editor_tabs.pop(index)
        if not self._editor_tabs:
            self._active_tab = -1
            self._current_id = None
            self._rebuild_tabs(0)
            self._set_editor_visible(False)
        elif was_active:
            next_index = min(index, len(self._editor_tabs) - 1)
            self._active_tab = -1
            self._rebuild_tabs(next_index)
            self._activate_tab(next_index)
        else:
            if index < self._active_tab:
                self._active_tab -= 1
            self._rebuild_tabs(self._active_tab)
        self._persist_tabs()
        self._update_window_title()

    def _close_tab_for_id(self, hotkey_id: str, ask: bool = True) -> None:
        index = self._tab_index(hotkey_id)
        if index < 0:
            return
        if ask:
            self._close_tab(index)
            return

        was_active = index == self._active_tab
        if was_active:
            self._commit_tab()
        self._editor_tabs.pop(index)
        if not self._editor_tabs:
            self._active_tab = -1
            self._current_id = None
            self._rebuild_tabs(0)
            self._set_editor_visible(False)
        elif was_active:
            next_index = min(index, len(self._editor_tabs) - 1)
            self._active_tab = -1
            self._rebuild_tabs(next_index)
            self._activate_tab(next_index)
        else:
            if index < self._active_tab:
                self._active_tab -= 1
            self._rebuild_tabs(self._active_tab)
        self._persist_tabs()

    def _toggle_editor(self) -> None:
        if self.ui.editorPanel.isHidden():
            row = self._selected_source_row()
            if row is not None:
                self._open_editor_for_id(self._model.entry(row).id)
            else:
                self._set_editor_visible(True)
        else:
            self._set_editor_visible(False)

    def _set_editor_visible(self, visible: bool) -> None:
        if not visible:
            self._commit_tab()
        self.ui.editorPanel.setVisible(visible)
        self.ui.actionToggleEditor.setChecked(visible)
        if visible:
            self.ui.centralSplitter.setSizes([NARROW_WIDTH, 750])
            self.resize(WIDE_WIDTH, WINDOW_HEIGHT)
            if self._editor_tabs:
                self._activate_tab(self._active_tab)
        else:
            self.resize(NARROW_WIDTH, WINDOW_HEIGHT)

    # ---------------------------------------------------------------- 运行/导出

    def _run_script(self) -> None:
        if self._active_tab < 0:
            QMessageBox.information(self, "运行", "请先打开一个脚本。")
            return
        self._commit_tab()
        tab = self._active_tab_object()
        if tab is None:
            return
        script = blocks_to_code(tab.blocks)
        if not script.strip():
            QMessageBox.information(self, "运行", "这个脚本还是空的。")
            return
        self._runner.submit(tab.hotkey_id, script)
        self.statusBar().showMessage("运行中…", 3000)

    def _run_entry(self, hotkey_id: str) -> None:
        row = self._model.row_of(hotkey_id)
        if row is None:
            return
        entry = self._model.entry(row)
        script = entry.script
        if not script.strip():
            QMessageBox.information(self, "运行", "这个脚本还是空的，先编辑并保存。")
            return
        self._runner.submit(hotkey_id, script)
        self.statusBar().showMessage("运行中…", 3000)

    def _export_python(self) -> None:
        tab = self._active_tab_object()
        if tab is not None:
            blocks = self.ui.blockEditor.blocks()
            name = self._tab_label(tab).rstrip(" *")
        else:
            row = self._selected_source_row()
            if row is None:
                QMessageBox.information(self, "导出 Python", "请先选中或打开一个脚本。")
                return
            entry = self._model.entry(row)
            blocks = entry.blocks
            name = entry.name or entry.key or "脚本"

        if not blocks:
            QMessageBox.information(self, "导出 Python", "这个脚本还没有积木。")
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

        default = self._library.directory / f"{safe_stem(name)}.py"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 Python 文件",
            str(default),
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

    def _save_all_metadata(self) -> None:
        self._save_timer.stop()
        for entry in self._model.entries():
            try:
                self._library.save(entry)
            except storage.StorageError as exc:
                logger.error("保存脚本失败 %s: %s", entry.name, exc)

    def _save_metadata(self, entry: HotKey) -> None:
        try:
            self._library.save(entry)
        except storage.StorageError as exc:
            logger.error("保存脚本失败 %s: %s", entry.name, exc)
            self.statusBar().showMessage(f"保存失败：{exc}", 6000)

    def _schedule_save(self) -> None:
        self._save_timer.start()

    # ---------------------------------------------------------------- 监听

    def _executable_entries(self) -> list[HotKey]:
        return [
            entry
            for entry in self._model.entries()
            if entry.enabled and entry.key and entry.script.strip()
        ]

    def _start_listening(self) -> None:
        entries = self._executable_entries()
        if not entries:
            QMessageBox.information(
                self,
                "没有可运行的热键",
                "请给脚本设置热键，并在编辑器里保存脚本。",
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
                self, "监听已停止", "热键重新注册失败，请检查组合键是否有效。"
            )

    def _set_listening(self, listening: bool) -> None:
        self._listening = listening
        self._update_actions()
        self._update_window_title()
        if self._tray is not None:
            self._tray.setToolTip(
                "HotKey · " + ("监听中" if listening else "已停止")
            )

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
            self.statusBar().showMessage("正在执行脚本…")

    def _on_script_finished(self, hotkey_id: str, ok: bool, message: str) -> None:
        row = self._model.row_of(hotkey_id)
        label = self._model.entry(row).name if row is not None else hotkey_id
        if ok:
            self.statusBar().showMessage(f"{label} 执行完成", 3000)
        else:
            logger.error("脚本 %s 执行失败: %s", label, message)
            self.statusBar().showMessage(f"{label} 执行失败：{message}", 8000)
            if self._tray is not None:
                self._tray.showMessage(
                    "脚本执行失败",
                    f"{label}\n{message}",
                    QSystemTrayIcon.MessageIcon.Warning,
                    4000,
                )

    def _on_hotkey_error(self, key: str, message: str) -> None:
        logger.error("热键 %s 注册失败: %s", key, message)
        self.statusBar().showMessage(f"热键 {key} 注册失败：{message}", 8000)

    # ---------------------------------------------------------------- 编辑器工具

    def _copy_value(self, text: str, label: str) -> None:
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage(
            f"{label} {text} 已复制；在积木输入框里粘贴", 8000
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

    # ---------------------------------------------------------------- 窗口/托盘

    def _focus_search(self) -> None:
        self.ui.searchEdit.setFocus()
        self.ui.searchEdit.selectAll()

    def _update_window_title(self) -> None:
        entry = self._active_entry()
        name = entry.name if entry is not None else ""
        state = "监听中" if self._listening else ""
        suffix = f"（{state}）" if state else ""
        self.setWindowTitle(f"HotKey - 脚本工具{suffix}")
        if hasattr(self, "title_bar"):
            self.title_bar.set_title(
                f"HotKey · {name}{suffix}" if name else f"HotKey{suffix}"
            )

    def _refresh_tab_labels(self) -> None:
        for index, tab in enumerate(self._editor_tabs):
            self.ui.editorTabs.setTabText(index, self._tab_label(tab))

    def _persist_tabs(self) -> None:
        settings = theme_module.settings()
        paths = []
        active_path = ""
        for index, tab in enumerate(self._editor_tabs):
            row = self._model.row_of(tab.hotkey_id)
            if row is None:
                continue
            entry = self._model.entry(row)
            if entry.path is None:
                continue
            paths.append(str(entry.path))
            if index == self._active_tab:
                active_path = str(entry.path)
        settings.setValue(SETTINGS_OPEN_TABS, paths)
        settings.setValue(SETTINGS_ACTIVE_TAB, active_path)

    def _restore_tabs(self) -> None:
        settings = theme_module.settings()
        raw = settings.value(SETTINGS_OPEN_TABS, [])
        if isinstance(raw, str):
            paths = [raw]
        elif isinstance(raw, (list, tuple)):
            paths = [str(path) for path in raw]
        else:
            paths = []

        for path_text in paths:
            path = Path(path_text)
            row = next(
                (
                    index
                    for index, entry in enumerate(self._model.entries())
                    if entry.path is not None and entry.path.resolve() == path.resolve()
                ),
                None,
            )
            if row is None:
                continue
            self._open_editor_for_id(self._model.entry(row).id)

        active_path = str(settings.value(SETTINGS_ACTIVE_TAB, ""))
        if active_path:
            for index, tab in enumerate(self._editor_tabs):
                row = self._model.row_of(tab.hotkey_id)
                if row is None:
                    continue
                entry = self._model.entry(row)
                if entry.path is not None and str(entry.path) == active_path:
                    self.ui.editorTabs.setCurrentIndex(index)
                    break

        if not self._editor_tabs:
            self._set_editor_visible(False)

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

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#151628"))
        painter.drawRoundedRect(2, 2, 60, 60, 14, 14)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#7F7FD5"), 3))
        painter.drawRoundedRect(5, 5, 54, 54, 11, 11)

        pen = QPen(QColor("#E5E5F7"), 5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(18, 21, 30, 31)
        painter.drawLine(30, 31, 18, 41)
        painter.drawLine(35, 43, 47, 43)
        painter.end()
        return QIcon(pixmap)

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

        self._commit_tab()
        if self._tray is not None:
            event.ignore()
            self.hide()
            self._tray.showMessage(
                "HotKey",
                "已最小化到托盘，脚本和热键继续运行。右键托盘图标可退出。",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            return

        self._hotkey_service.stop()
        self._runner.shutdown()
        event.accept()

    def _quit(self) -> None:
        self._commit_tab()

        dirty = [tab for tab in self._editor_tabs if tab.dirty]
        if dirty:
            answer = QMessageBox.question(
                self,
                "未保存的脚本",
                f"有 {len(dirty)} 个标签还没保存，要保存吗？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if answer == QMessageBox.StandardButton.Cancel:
                return
            if answer == QMessageBox.StandardButton.Save:
                for index, tab in enumerate(list(self._editor_tabs)):
                    if tab.dirty and not self._save_tab(index):
                        return

        self._save_all_metadata()
        self._quitting = True
        self._hotkey_service.stop()
        self._runner.shutdown()
        if self._tray is not None:
            self._tray.hide()
        QApplication.quit()
