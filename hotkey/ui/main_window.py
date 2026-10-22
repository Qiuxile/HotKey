"""主窗口：组合 Designer 生成的 Ui_MainWindow。"""

from __future__ import annotations

from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QMainWindow

from hotkey.ui.generated.ui_main_window import Ui_MainWindow

WINDOW_HEIGHT = 560
NARROW_WIDTH = 370
WIDE_WIDTH = 1120


class MainWindow(QMainWindow):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._setup_table()
        self._connect_signals()
        self._set_editor_visible(False)
        self.statusBar().showMessage("就绪")

    # ------------------------------------------------------------------ 初始化

    def _setup_table(self) -> None:
        # M2 会替换成 HotKeyTableModel + QSortFilterProxyModel
        model = QStandardItemModel(0, 2, self)
        model.setHorizontalHeaderLabels(["热键", "描述"])
        self.ui.hotkeyTable.setModel(model)
        self.ui.hotkeyTable.setColumnWidth(0, 140)
        self.ui.hotkeyTable.horizontalHeader().setStretchLastSection(True)
        self.ui.hotkeyTable.verticalHeader().setVisible(False)

    def _connect_signals(self) -> None:
        self.ui.actionQuit.triggered.connect(self.close)
        self.ui.actionSearch.triggered.connect(self._focus_search)
        self.ui.actionToggleEditor.triggered.connect(self._toggle_editor)
        self.ui.btnCloseEditor.clicked.connect(
            lambda: self._set_editor_visible(False)
        )

    # ------------------------------------------------------------------ 行为

    def _focus_search(self) -> None:
        self.ui.searchEdit.setFocus()
        self.ui.searchEdit.selectAll()

    def _toggle_editor(self) -> None:
        self._set_editor_visible(self.ui.editorPanel.isHidden())

    def _set_editor_visible(self, visible: bool) -> None:
        self.ui.editorPanel.setVisible(visible)
        self.ui.actionToggleEditor.setChecked(visible)
        if visible:
            self.ui.centralSplitter.setSizes([NARROW_WIDTH, 750])
            self.resize(WIDE_WIDTH, WINDOW_HEIGHT)
        else:
            self.resize(NARROW_WIDTH, WINDOW_HEIGHT)
