"""右侧积木栏：只接受拖入的中文积木，不提供自由输入。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
)

from hotkey.core import catalog
from hotkey.core.models import Block
from hotkey.ui.widgets.statement_tree import SNIPPET_MIME

KIND_ROLE = Qt.ItemDataRole.UserRole
OLD_TEXT_ROLE = Qt.ItemDataRole.UserRole + 1
EMPTY_KIND = "empty"
EMPTY_TEXT = "空"


class BlockTree(QTreeWidget):
    """积木列表。

    - 从左侧拖入：插入到目标位置（悬停在 for/if 中间会成为子块）
    - 选中后按空格：编辑该块文字（参数）
    - Delete：删除该块及其子块
    """

    changed = Signal()
    message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(18)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setAcceptDrops(True)

        self._loading = False
        self.itemDoubleClicked.connect(self._remember_text)
        self.itemChanged.connect(self._on_item_changed)
        self.customContextMenuRequested.connect(self._show_menu)

    # ---------------------------------------------------------------- 读写

    def load_blocks(self, blocks: list[Block]) -> None:
        self._loading = True
        try:
            self.clear()
            for block in blocks:
                self.addTopLevelItem(self._build_item(block))
            self.expandAll()
        finally:
            self._loading = False

    def blocks(self) -> list[Block]:
        return [
            self._item_block(self.topLevelItem(index))
            for index in range(self.topLevelItemCount())
        ]

    def append_snippet(
        self, snippet_id: str, parent: QTreeWidgetItem | None = None
    ) -> QTreeWidgetItem:
        item = self._create_item(snippet_id)
        if parent is not None and catalog.is_container(
            str(parent.data(0, KIND_ROLE))
        ):
            parent.addChild(item)
            parent.setExpanded(True)
        elif parent is not None:
            grandparent = parent.parent()
            if grandparent is None:
                index = self.indexOfTopLevelItem(parent) + 1
                self.insertTopLevelItem(index, item)
            else:
                index = grandparent.indexOfChild(parent) + 1
                grandparent.insertChild(index, item)
        else:
            self.addTopLevelItem(item)

        self.setCurrentItem(item)
        self.changed.emit()
        return item

    def _build_item(self, block: Block) -> QTreeWidgetItem:
        text = block.text
        if block.kind == EMPTY_KIND and not text:
            text = EMPTY_TEXT
        item = QTreeWidgetItem([text])
        item.setData(0, KIND_ROLE, block.kind)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        item.setToolTip(0, "选中后按空格编辑")
        for child in block.children:
            item.addChild(self._build_item(child))
        return item

    def _item_block(self, item: QTreeWidgetItem) -> Block:
        kind = str(item.data(0, KIND_ROLE) or "")
        text = item.text(0)
        if kind == EMPTY_KIND and text == EMPTY_TEXT:
            text = ""

        children: list[Block] = []
        if catalog.is_container(kind):
            children = [
                self._item_block(item.child(index))
                for index in range(item.childCount())
            ]
        return Block(kind=kind, text=text, children=children)

    def _create_item(self, snippet_id: str) -> QTreeWidgetItem:
        if snippet_id == EMPTY_KIND:
            text = EMPTY_TEXT
        else:
            text = catalog.snippet(snippet_id).blank_text()

        item = QTreeWidgetItem([text])
        item.setData(0, KIND_ROLE, snippet_id)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        item.setToolTip(0, "选中后按空格编辑")
        return item

    # ---------------------------------------------------------------- 拖放

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        if not mime.hasFormat(SNIPPET_MIME):
            super().dropEvent(event)
            return

        snippet_id = bytes(mime.data(SNIPPET_MIME)).decode("utf-8", errors="replace")
        if snippet_id != EMPTY_KIND:
            try:
                catalog.snippet(snippet_id)
            except KeyError:
                event.ignore()
                return

        position = event.position().toPoint()
        target, where = self._drop_target(position)
        item = self._create_item(snippet_id)
        self._insert_item(item, target, where)
        self.setCurrentItem(item)
        self.changed.emit()
        event.acceptProposedAction()

    def _drop_target(
        self, position
    ) -> tuple[QTreeWidgetItem | None, str]:
        target = self.itemAt(position)
        if target is None:
            return None, "root"

        rect = self.visualItemRect(target)
        if position.y() < rect.top() + rect.height() // 3:
            return target, "above"
        if position.y() > rect.bottom() - rect.height() // 3:
            return target, "below"

        kind = str(target.data(0, KIND_ROLE) or "")
        if catalog.is_container(kind):
            return target, "child"
        return target, "below"

    def _insert_item(
        self,
        item: QTreeWidgetItem,
        target: QTreeWidgetItem | None,
        where: str,
    ) -> None:
        if target is None or where == "root":
            self.addTopLevelItem(item)
            return

        if where == "child":
            target.addChild(item)
            target.setExpanded(True)
            return

        parent = target.parent()
        if parent is None:
            index = self.indexOfTopLevelItem(target)
            if where == "below":
                index += 1
            self.insertTopLevelItem(index, item)
        else:
            index = parent.indexOfChild(target)
            if where == "below":
                index += 1
            parent.insertChild(index, item)

    # ---------------------------------------------------------------- 编辑

    def _remember_text(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        item.setData(0, OLD_TEXT_ROLE, item.text(0))

    def _is_editing(self) -> bool:
        return self.state() == QAbstractItemView.State.EditingState

    def _begin_edit(self, item: QTreeWidgetItem) -> None:
        self._remember_text(item)
        self.editItem(item, 0)

    def _on_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._loading:
            return

        kind = str(item.data(0, KIND_ROLE) or "")
        text = item.text(0)

        if kind == EMPTY_KIND:
            if not text.strip():
                self._loading = True
                item.setText(0, EMPTY_TEXT)
                self._loading = False
            self.changed.emit()
            return

        try:
            snippet = catalog.snippet(kind)
        except KeyError:
            return

        if snippet.parse(text) is None:
            fallback = item.data(0, OLD_TEXT_ROLE) or snippet.blank_text()
            self._loading = True
            item.setText(0, str(fallback))
            self._loading = False
            self.message.emit(f"无法识别「{text}」，已还原")
            return

        self.changed.emit()

    # ---------------------------------------------------------------- 键盘/菜单

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Space and not self._is_editing():
            item = self.currentItem()
            if item is not None:
                self._begin_edit(item)
                return

        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            item = self.currentItem()
            if item is not None:
                self._remove_item(item)
                return

        super().keyPressEvent(event)

    def _show_menu(self, position) -> None:
        item = self.itemAt(position)
        if item is None:
            return
        self.setCurrentItem(item)
        menu = QMenu(self)
        menu.addAction("编辑", lambda: self._begin_edit(item))
        menu.addAction("删除", lambda: self._remove_item(item))
        menu.exec(self.viewport().mapToGlobal(position))

    def _remove_item(self, item: QTreeWidgetItem) -> None:
        parent = item.parent()
        if parent is None:
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        else:
            parent.removeChild(item)
        self.changed.emit()
