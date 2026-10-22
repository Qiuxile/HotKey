"""操作面板树：分类 + 可拖拽积木 + 顶部「空」块。"""

from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem

from hotkey.core import catalog

SNIPPET_MIME = "application/x-hotkey-snippet"
EMPTY_KIND = "empty"


class StatementTree(QTreeWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setIndentation(14)
        self._populate()

    def _populate(self) -> None:
        empty_item = QTreeWidgetItem(["空"])
        empty_item.setData(0, Qt.ItemDataRole.UserRole, EMPTY_KIND)
        empty_item.setToolTip(0, "拖入右侧后自己填写代码")
        self.addTopLevelItem(empty_item)

        grouped = catalog.snippets_by_category()
        for category in catalog.CATEGORIES:
            top = QTreeWidgetItem([category.label])
            top.setFlags(Qt.ItemFlag.ItemIsEnabled)
            for snippet in grouped.get(category.id, []):
                if snippet.hidden:
                    continue
                display = snippet.render(snippet.blank_values())
                child = QTreeWidgetItem([display])
                child.setData(0, Qt.ItemDataRole.UserRole, snippet.id)
                child.setToolTip(0, display)
                top.addChild(child)
            self.addTopLevelItem(top)
            top.setExpanded(True)

    def startDrag(self, supported_actions) -> None:  # noqa: N802 - Qt 接口
        item = self.currentItem()
        if item is None:
            return
        snippet_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not snippet_id:
            return

        mime = QMimeData()
        mime.setData(SNIPPET_MIME, str(snippet_id).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)
