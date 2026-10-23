"""操作面板树：分类 + 可拖拽积木 + 顶部「空」块。"""

from __future__ import annotations

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem

from hotkey.core import catalog

SNIPPET_MIME = "application/x-hotkey-snippet"
EMPTY_KIND = "empty"


class StatementTree(QTreeWidget):
    """积木柜：分类树 + 搜索过滤。"""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setIndentation(14)
        self._leaf_items: list[tuple[QTreeWidgetItem, str]] = []
        self._category_items: list[tuple[QTreeWidgetItem, list[QTreeWidgetItem]]] = []
        self._empty_item: QTreeWidgetItem | None = None
        self._no_result_item: QTreeWidgetItem | None = None
        self._populate()

    def _populate(self) -> None:
        empty_item = QTreeWidgetItem(["空"])
        empty_item.setData(0, Qt.ItemDataRole.UserRole, EMPTY_KIND)
        empty_item.setToolTip(0, "拖入右侧后自己填写代码")
        self.addTopLevelItem(empty_item)
        self._empty_item = empty_item

        grouped = catalog.snippets_by_category()
        for category in catalog.CATEGORIES:
            top = QTreeWidgetItem([category.label])
            top.setFlags(Qt.ItemFlag.ItemIsEnabled)
            children: list[QTreeWidgetItem] = []
            for snippet in grouped.get(category.id, []):
                if snippet.hidden:
                    continue
                display = snippet.preview()
                child = QTreeWidgetItem([display])
                child.setData(0, Qt.ItemDataRole.UserRole, snippet.id)
                child.setToolTip(
                    0, f"{display}\n\n{snippet.code}"
                )
                top.addChild(child)
                children.append(child)
                self._leaf_items.append(
                    (
                        child,
                        f"{display} {snippet.id} {snippet.code} "
                        f"{category.label}".lower(),
                    )
                )
            self.addTopLevelItem(top)
            top.setExpanded(True)
            self._category_items.append((top, children))

        no_result = QTreeWidgetItem(["没有匹配的积木"])
        no_result.setFlags(Qt.ItemFlag.NoItemFlags)
        no_result.setHidden(True)
        self.addTopLevelItem(no_result)
        self._no_result_item = no_result

    def set_filter(self, text: str) -> None:
        """按中文预览、id、Python 代码、分类过滤积木。"""
        needle = text.strip().lower()
        if not needle:
            self._show_all()
            return

        any_visible = False
        for item, haystack in self._leaf_items:
            visible = needle in haystack
            item.setHidden(not visible)
            any_visible = any_visible or visible

        if self._empty_item is not None:
            empty_visible = "空" in needle or "empty" in needle
            self._empty_item.setHidden(not empty_visible)
            any_visible = any_visible or empty_visible

        for category_item, children in self._category_items:
            has_visible = any(not child.isHidden() for child in children)
            category_item.setHidden(not has_visible)
            if has_visible:
                category_item.setExpanded(True)

        if self._no_result_item is not None:
            self._no_result_item.setHidden(any_visible)

    def _show_all(self) -> None:
        for item, _haystack in self._leaf_items:
            item.setHidden(False)
        if self._empty_item is not None:
            self._empty_item.setHidden(False)
        for category_item, _children in self._category_items:
            category_item.setHidden(False)
        if self._no_result_item is not None:
            self._no_result_item.setHidden(True)

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
