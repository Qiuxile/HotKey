"""操作面板树：分类 + 可拖拽积木 + 顶部「空」块。"""

from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDrag, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
)

from hotkey.core import catalog

SNIPPET_MIME = "application/x-hotkey-snippet"
EMPTY_KIND = "empty"
PYTHON_KIND = "python"


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
        self._no_result_item: QTreeWidgetItem | None = None
        self._populate()

    def _populate(self) -> None:
        grouped = catalog.snippets_by_category()
        for category in catalog.CATEGORIES:
            top = QTreeWidgetItem([category.label])
            top.setFlags(Qt.ItemFlag.ItemIsEnabled)
            children: list[QTreeWidgetItem] = []

            if category.id == "python":
                for label, kind in (
                    ("Python代码行", EMPTY_KIND),
                    ("Python代码", PYTHON_KIND),
                ):
                    child = QTreeWidgetItem([label])
                    child.setData(0, Qt.ItemDataRole.UserRole, kind)
                    tip = (
                        "只能输入一行 Python 代码"
                        if kind == EMPTY_KIND
                        else "可以输入任意行 Python 代码"
                    )
                    child.setToolTip(0, tip)
                    top.addChild(child)
                    children.append(child)
                    self._leaf_items.append(
                        (child, f"{label} {kind} python代码".lower())
                    )
            else:
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
        for category_item, _children in self._category_items:
            category_item.setHidden(False)
        if self._no_result_item is not None:
            self._no_result_item.setHidden(True)

    def all_expanded(self) -> bool:
        return all(
            category_item.isExpanded()
            for category_item, _children in self._category_items
        )

    def set_all_expanded(self, expanded: bool) -> None:
        for category_item, _children in self._category_items:
            category_item.setExpanded(expanded)

    def toggle_all_expanded(self) -> bool:
        expanded = not self.all_expanded()
        self.set_all_expanded(expanded)
        return expanded

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

        accent = "#7F7FD5"
        if snippet_id in (EMPTY_KIND, PYTHON_KIND):
            accent = catalog.category("python").accent
        else:
            try:
                snippet = catalog.snippet(str(snippet_id))
                accent = catalog.category(snippet.category).accent
            except KeyError:
                pass
        pixmap = self._drag_pixmap(item.text(0), accent)
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(12, min(20, pixmap.height() // 2)))
        drag.exec(Qt.DropAction.CopyAction)

    def _drag_pixmap(self, text: str, accent: str) -> QPixmap:
        """画一个和积木外观一致的小预览，跟随鼠标拖动。"""
        shown = self.fontMetrics().elidedText(
            text, Qt.TextElideMode.ElideRight, 240
        )
        preview = QFrame(self)
        preview.setObjectName("dragPreview")
        preview.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        preview.setStyleSheet(
            "QFrame#dragPreview {"
            " background-color: #151628;"
            " border: 1px solid #2D2B55;"
            f" border-left: 4px solid {accent};"
            " border-radius: 4px;"
            "}"
            "QLabel { color: #E5E5F7; background: transparent;"
            " padding: 2px 4px; }"
        )
        layout = QHBoxLayout(preview)
        layout.setContentsMargins(7, 4, 9, 4)
        label = QLabel(shown, preview)
        layout.addWidget(label)
        preview.ensurePolished()
        preview.adjustSize()
        pixmap = preview.grab()
        preview.deleteLater()
        return pixmap
