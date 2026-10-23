"""主窗口：脚本库、编辑标签与试运行；热键监听在独立进程。"""

from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QEvent, QModelIndex, QObject, QPoint, QSize, QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizeGrip,
    QVBoxLayout,
    QWidget,
)

from hotkey.core import keymap, storage, validator
from hotkey.core.blocks import blocks_to_code
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
from hotkey.ui.widgets.frameless_resize import FramelessResizer
from hotkey.ui.widgets.title_bar import TitleBar

logger = logging.getLogger("HotKey.Window")

WINDOW_HEIGHT = 600
NARROW_WIDTH = 400
WIDE_WIDTH = 1240
SETTINGS_OPEN_TABS = "open_scripts"
SETTINGS_ACTIVE_TAB = "active_script"


@dataclass
class EditorTab:
    """右侧一个编辑标签的内存状态。"""

    hotkey_id: str
    blocks: list[Block] = field(default_factory=list)
    dirty: bool = False


class _Signals(QObject):
    """把 runner 线程的回调安全地转发到主线程。"""

    started = Signal(str)
    finished = Signal(str, bool, str)


class MainWindow(QMainWindow):
    """编辑器窗口：脚本库 + 编辑标签 + 试运行；监听器在独立进程。"""

    def __init__(self, library_dir: Path | None = None) -> None:
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # 编辑区先从 splitter 里摘掉，避免隐藏时仍把窗口最小高度撑到 700
        self.ui.editorPanel.hide()
        self.ui.editorPanel.setParent(None)
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

        self._editor_auto_expanded = False
        self._editor_previous_size = QSize(NARROW_WIDTH, WINDOW_HEIGHT)

        self._signals = _Signals(self)
        self._runner = ScriptRunner(
            on_started=self._signals.started.emit,
            on_finished=self._signals.finished.emit,
        )

        self._setup_chrome()
        self.resizer = FramelessResizer(self)
        self._configure_table()
        self._connect_signals()
        self._load_library()
        self._init_theme()
        self._set_editor_visible(False)
        self._update_actions()

        # 所有布局/隐藏动作完成后再固定窄窗口尺寸
        self.setMinimumWidth(NARROW_WIDTH)
        self.resize(NARROW_WIDTH, WINDOW_HEIGHT)
        self._restore_tabs()

    # ---------------------------------------------------------------- 外观

    def _setup_chrome(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setMinimumSize(NARROW_WIDTH, 520)

        self.title_bar = TitleBar(self)
        self.title_bar.theme_clicked.connect(self._toggle_theme)

        chrome = QWidget(self)
        layout = QVBoxLayout(chrome)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.title_bar)
        self.setMenuWidget(chrome)

        # 不用 QMainWindow 自带的菜单栏：用标题栏按钮承载同样的 QAction
        self.title_bar.attach_menus(
            [
                (self.ui.menuFile.title(), self.ui.menuFile.actions()),
                (self.ui.menuEdit.title(), self.ui.menuEdit.actions()),
                (self.ui.menuAction.title(), self.ui.menuAction.actions()),
            ]
        )
        self.ui.menubar.hide()
        self.ui.menubar.setParent(None)

        self.ui.statusbar.addPermanentWidget(QSizeGrip(self), 0)
        self.resize(NARROW_WIDTH, WINDOW_HEIGHT)

    # ---------------------------------------------------------------- 窗口缩放

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

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        if event.type() == QEvent.Type.WindowStateChange and hasattr(
            self, "title_bar"
        ):
            self.title_bar.set_maximized(self.isMaximized())
            if self.isMaximized() or self.isFullScreen():
                self._editor_auto_expanded = False
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
        self.ui.paletteSearch.textChanged.connect(
            self.ui.statementTree.set_filter
        )
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
        """选择文件名并创建空脚本，然后打开它的编辑标签。"""
        target = self._choose_new_script_path()
        if target is None:
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

    def _choose_new_script_path(self) -> Path | None:
        default = self._library.directory / "新脚本.hk"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "新建脚本",
            str(default),
            "HotKey 脚本 (*.hk);;所有文件 (*)",
        )
        if not path:
            return None

        target = Path(path)
        if self._library.directory.resolve() != target.resolve().parent:
            QMessageBox.warning(
                self,
                "路径不支持",
                f"脚本必须直接保存在脚本目录里：\n{self._library.directory}",
            )
            return None
        if target.suffix.lower() != ".hk":
            target = target.with_suffix(".hk")

        for entry in self._model.entries():
            if entry.path is not None and entry.path.resolve() == target.resolve():
                QMessageBox.warning(
                    self,
                    "脚本已存在",
                    f"「{entry.name}」已经使用了这个文件，请换一个名字。",
                )
                return None
        return target

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

    def _clear_hotkey(self, row: int) -> None:
        entry = self._model.entry(row)
        entry.key = ""
        self._model.touch(row)
        self._save_metadata(entry)
        self._refresh_tab_labels()
        self.statusBar().showMessage("已清除热键，脚本仍可手动运行/导出", 5000)

    def _show_context_menu(self, position: QPoint) -> None:
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

    def _open_editor_from_index(self, index: QModelIndex) -> None:
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
        """校验并保存一个标签；返回 False 表示用户取消或校验失败。"""
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
        self.ui.editorTabs.setTabText(index, self._tab_label(tab))
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
        """显示/隐藏右侧编辑区；只在安全条件下自动调整窗口大小。"""
        was_hidden = self.ui.editorPanel.isHidden()

        if visible and was_hidden:
            self._open_editor_panel()
        elif not visible:
            self._close_editor_panel()

        self._commit_tab()
        self.ui.editorPanel.setVisible(visible)
        if not visible:
            self.ui.editorPanel.setParent(None)
        self.ui.actionToggleEditor.setChecked(visible)
        if visible and self._editor_tabs:
            self._activate_tab(self._active_tab)

    def _is_default_narrow_window(self) -> bool:
        return (
            not self.isMaximized()
            and not self.isFullScreen()
            and self.width() == NARROW_WIDTH
            and self.height() == WINDOW_HEIGHT
        )

    def _open_editor_panel(self) -> None:
        if self.ui.editorPanel.parent() is not self.ui.centralSplitter:
            self.ui.centralSplitter.addWidget(self.ui.editorPanel)

        # 用户手动调过大小、最大化或全屏时，只显示面板，不动窗口。
        self._editor_auto_expanded = self._is_default_narrow_window()
        if self._editor_auto_expanded:
            self._editor_previous_size = self.size()
            self.resize(WIDE_WIDTH, WINDOW_HEIGHT)
            self.ui.centralSplitter.setSizes(
                [NARROW_WIDTH, WIDE_WIDTH - NARROW_WIDTH]
            )

    def _close_editor_panel(self) -> None:
        if (
            self._editor_auto_expanded
            and not self.isMaximized()
            and not self.isFullScreen()
            and self.size() == QSize(WIDE_WIDTH, WINDOW_HEIGHT)
        ):
            self.resize(self._editor_previous_size)
        self._editor_auto_expanded = False

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
        """把当前标签（或选中脚本）导出为独立可运行的 .py。"""
        selection = self._export_selection()
        if selection is None:
            return
        blocks, name = selection

        source = self._build_export_source(blocks)
        if source is None:
            return
        target = self._ask_export_path(name)
        if target is None:
            return
        self._write_export(target, source)

    def _export_selection(self) -> tuple[list[Block], str] | None:
        tab = self._active_tab_object()
        if tab is not None:
            blocks = self.ui.blockEditor.blocks()
            name = self._tab_label(tab).rstrip(" *")
        else:
            row = self._selected_source_row()
            if row is None:
                QMessageBox.information(
                    self, "导出 Python", "请先选中或打开一个脚本。"
                )
                return None
            entry = self._model.entry(row)
            blocks = entry.blocks
            name = entry.name or entry.key or "脚本"

        if not blocks:
            QMessageBox.information(self, "导出 Python", "这个脚本还没有积木。")
            return None
        return blocks, name

    def _build_export_source(self, blocks: list[Block]) -> str | None:
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
            return None
        return source

    def _ask_export_path(self, name: str) -> Path | None:
        default = self._library.directory / f"{safe_stem(name)}.py"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出 Python 文件",
            str(default),
            "Python 文件 (*.py);;所有文件 (*)",
        )
        return Path(path) if path else None

    def _write_export(self, target: Path, source: str) -> None:
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
        """退出/关闭前把所有脚本的元数据和已保存脚本写回磁盘。"""
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

    # ---------------------------------------------------------------- 监听

    def _start_listening(self) -> None:
        from hotkey.listener import is_listener_running, launch_listener

        if is_listener_running():
            self._set_listening(True)
            self.statusBar().showMessage("监听器已经在运行", 4000)
            return
        if not launch_listener():
            QMessageBox.critical(
                self, "启动失败", "无法启动监听器进程，请检查程序路径。"
            )
            return
        self._set_listening(True)
        self.statusBar().showMessage("监听器已启动，窗口关闭后仍会继续", 5000)
        QTimer.singleShot(700, self._verify_listener_start)

    def _verify_listener_start(self) -> None:
        from hotkey.listener import is_listener_running

        if not is_listener_running():
            self._set_listening(False)
            QMessageBox.warning(
                self,
                "监听器未启动",
                "监听器进程没有响应，请查看配置目录下的 listener.log。",
            )

    def _stop_listening(self) -> None:
        from hotkey.listener import stop_listener

        if stop_listener():
            self.statusBar().showMessage("监听器已退出", 4000)
        else:
            self.statusBar().showMessage("监听器没有在运行", 4000)
        self._set_listening(False)

    def _set_listening(self, listening: bool) -> None:
        self._listening = listening
        self._update_actions()
        self._update_window_title()

    def _update_actions(self) -> None:
        self.ui.actionStart.setEnabled(not self._listening)
        self.ui.actionStop.setEnabled(self._listening)

    def _on_script_started(self, _hotkey_id: str) -> None:
        self.statusBar().showMessage("正在执行脚本…")

    def _on_script_finished(self, hotkey_id: str, ok: bool, message: str) -> None:
        row = self._model.row_of(hotkey_id)
        label = self._model.entry(row).name if row is not None else hotkey_id
        if ok:
            self.statusBar().showMessage(f"{label} 执行完成", 3000)
            return
        logger.error("脚本 %s 执行失败: %s", label, message)
        self.statusBar().showMessage(f"{label} 执行失败：{message}", 8000)
        QMessageBox.warning(self, "试运行失败", f"{label}\n{message}")

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
        """把打开的标签路径写入 settings.ini，供下次启动恢复。"""
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
        """恢复上次打开的标签；路径已不存在的静默跳过。"""
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

    def _confirm_save_dirty_tabs(self) -> bool:
        """关闭编辑器前询问保存；返回 False 表示取消关闭。"""
        dirty = [tab for tab in self._editor_tabs if tab.dirty]
        if not dirty:
            return True

        answer = QMessageBox.question(
            self,
            "未保存的脚本",
            f"有 {len(dirty)} 个标签还没保存，要保存吗？",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            for index, tab in enumerate(list(self._editor_tabs)):
                if tab.dirty and not self._save_tab(index):
                    return False
        return True

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if not self._quitting:
            self._commit_tab()
            if not self._confirm_save_dirty_tabs():
                event.ignore()
                return
            self._runner.shutdown()
        event.accept()

    def _quit(self) -> None:
        self._commit_tab()
        if not self._confirm_save_dirty_tabs():
            return
        self._save_all_metadata()
        self._quitting = True
        self._runner.shutdown()
        QApplication.quit()
