"""右侧积木栏：常驻参数输入框 + 拖放 + 嵌套（Scratch 风格列表）。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRegularExpression, Qt, Signal
from PySide6.QtGui import QFontDatabase, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QSizePolicy,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from hotkey.core import catalog
from hotkey.core.models import Block
from hotkey.ui.widgets.statement_tree import SNIPPET_MIME

KIND_ROLE = Qt.ItemDataRole.UserRole
BLOCK_ROLE = Qt.ItemDataRole.UserRole + 1
EMPTY_KIND = "empty"


class BlockRow(QFrame):
    """一行积木：中文文字 + 常驻参数输入框 + 删除按钮。"""

    changed = Signal()
    delete_requested = Signal(object)

    def __init__(
        self,
        snippet: catalog.Snippet | None,
        block: Block,
        item: QTreeWidgetItem,
        tree: "BlockTree",
    ) -> None:
        super().__init__(tree)
        self.setObjectName("blockRow")
        self.block = block
        self._snippet = snippet
        self._item = item
        self._tree = tree
        self._fields: dict[str, QLineEdit] = {}
        self._selected = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 8, 5)
        layout.setSpacing(5)

        if snippet is None:
            self._build_empty(layout, block)
        else:
            self._build_snippet(layout, snippet, block)

        delete_button = QToolButton(self)
        delete_button.setText("✕")
        delete_button.setToolTip("删除这块积木")
        delete_button.setAutoRaise(True)
        delete_button.setFixedSize(22, 22)
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self._item))
        layout.addWidget(delete_button)

        self._apply_style()
        self.setMinimumHeight(38)

        for child in [self, *self.findChildren(QWidget)]:
            child.installEventFilter(self)

    # ---------------------------------------------------------------- 构建

    def _build_empty(self, layout: QHBoxLayout, block: Block) -> None:
        edit = QLineEdit(block.text, self)
        edit.setPlaceholderText("在这里写一行 Python 代码")
        edit.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        edit.setMinimumWidth(220)
        edit.setFixedHeight(28)
        edit.setAcceptDrops(False)
        edit.textChanged.connect(self._on_code_changed)
        layout.addWidget(edit, 1)
        self._fields[""] = edit

    def _build_snippet(
        self,
        layout: QHBoxLayout,
        snippet: catalog.Snippet,
        block: Block,
    ) -> None:
        has_growing_field = False

        for segment in snippet.segments():
            if isinstance(segment, catalog.Param):
                edit = QLineEdit(block.params.get(segment.name, ""), self)
                edit.setPlaceholderText(segment.placeholder)
                edit.setFixedHeight(26)
                edit.setAcceptDrops(False)

                if segment.kind == "number":
                    edit.setValidator(
                        QRegularExpressionValidator(
                            QRegularExpression(r"-?\d*"), edit
                        )
                    )
                    edit.setFixedWidth(segment.width)
                    layout.addWidget(edit)
                else:
                    edit.setMinimumWidth(segment.width)
                    edit.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Fixed,
                    )
                    layout.addWidget(edit, 1)
                    has_growing_field = True

                edit.textChanged.connect(
                    lambda text, name=segment.name: self._on_param_changed(
                        name, text
                    )
                )
                self._fields[segment.name] = edit
            else:
                label = QLabel(segment, self)
                label.setStyleSheet("background: transparent; color: #1f2937;")
                layout.addWidget(label)

        if not has_growing_field:
            layout.addStretch(1)

    # ---------------------------------------------------------------- 数据

    def _on_param_changed(self, name: str, text: str) -> None:
        self.block.params[name] = text
        if self._snippet is not None:
            self.block.text = self._snippet.render(self.block.params)
        self.changed.emit()

    def _on_code_changed(self, text: str) -> None:
        self.block.text = text
        self.changed.emit()

    def values(self) -> dict[str, str]:
        return dict(self.block.params)

    def field(self, name: str) -> QLineEdit | None:
        return self._fields.get(name)

    def code_edit(self) -> QLineEdit | None:
        return self._fields.get("")

    def set_selected(self, selected: bool) -> None:
        if selected == self._selected:
            return
        self._selected = selected
        self._apply_style()

    def _apply_style(self) -> None:
        if self._snippet is None:
            color, accent = "#f1f5f9", "#94a3b8"
        else:
            category = catalog.category(self._snippet.category)
            color, accent = category.color, category.accent

        border = f"2px solid {accent}" if self._selected else f"1px solid {accent}66"
        self.setStyleSheet(
            f"QFrame#blockRow {{ background-color: {color}; "
            f"border: {border}; border-radius: 7px; }}"
        )

    # ---------------------------------------------------------------- 拖放转发

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt 接口
        event_type = event.type()

        if event_type in (
            QEvent.Type.DragEnter,
            QEvent.Type.DragMove,
            QEvent.Type.Drop,
        ):
            point = obj.mapToGlobal(event.position().toPoint())
            return self._tree.handle_external_drag(event, point)

        if event_type == QEvent.Type.MouseButtonPress:
            self._tree.setCurrentItem(self._item)

        return super().eventFilter(obj, event)


class BlockTree(QTreeWidget):
    """Scratch 风格的积木列表。"""

    changed = Signal()
    message = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(22)
        self.setUniformRowHeights(False)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.header().setStretchLastSection(True)

        self.currentItemChanged.connect(self._on_current_changed)
        self.customContextMenuRequested.connect(self._show_menu)

    # ---------------------------------------------------------------- 读写

    def load_blocks(self, blocks: list[Block]) -> None:
        self.clear()
        for block in blocks:
            item = self._build_item(block)
            self.addTopLevelItem(item)
            self._attach_rows(item)
        self.expandAll()

    def blocks(self) -> list[Block]:
        return [
            self._item_block(self.topLevelItem(index))
            for index in range(self.topLevelItemCount())
        ]

    def append_snippet(
        self, snippet_id: str, parent: QTreeWidgetItem | None = None
    ) -> QTreeWidgetItem:
        block = self._new_block(snippet_id)
        item = self._build_item(block)

        if parent is not None and catalog.is_container(
            str(parent.data(0, KIND_ROLE))
        ):
            parent.addChild(item)
            parent.setExpanded(True)
        elif parent is not None:
            grandparent = parent.parent()
            if grandparent is None:
                self.insertTopLevelItem(self.indexOfTopLevelItem(parent) + 1, item)
            else:
                grandparent.insertChild(grandparent.indexOfChild(parent) + 1, item)
        else:
            self.addTopLevelItem(item)

        self._attach_rows(item)
        self.setCurrentItem(item)
        self.scrollToItem(item)
        self.changed.emit()
        return item

    def _new_block(self, snippet_id: str) -> Block:
        if snippet_id == EMPTY_KIND:
            return Block(kind=EMPTY_KIND, text="")
        snippet = catalog.snippet(snippet_id)
        params = snippet.blank_values()
        return Block(kind=snippet_id, text=snippet.render(params), params=params)

    def _build_item(self, block: Block) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setData(0, KIND_ROLE, block.kind)
        item.setData(0, BLOCK_ROLE, block)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

        for child in block.children:
            item.addChild(self._build_item(child))

        return item

    def _attach_rows(self, item: QTreeWidgetItem) -> None:
        """item 必须先加入树，setItemWidget 才会生效。"""
        block = item.data(0, BLOCK_ROLE)
        kind = str(item.data(0, KIND_ROLE) or "")
        if isinstance(block, Block):
            snippet = None if kind == EMPTY_KIND else catalog.snippet(kind)
            row = BlockRow(snippet, block, item, self)
            row.changed.connect(self.changed.emit)
            row.delete_requested.connect(self.remove_item)
            self.setItemWidget(item, 0, row)
            item.setSizeHint(0, row.sizeHint())

        for index in range(item.childCount()):
            self._attach_rows(item.child(index))

    def _item_block(self, item: QTreeWidgetItem) -> Block:
        stored = item.data(0, BLOCK_ROLE)
        kind = str(item.data(0, KIND_ROLE) or "")

        if isinstance(stored, Block):
            text = stored.text
            params = dict(stored.params)
        else:
            text, params = "", {}

        children: list[Block] = []
        if catalog.is_container(kind):
            children = [
                self._item_block(item.child(index))
                for index in range(item.childCount())
            ]
        return Block(kind=kind, text=text, params=params, children=children)

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
        if event.mimeData().hasFormat(SNIPPET_MIME):
            global_point = self.viewport().mapToGlobal(
                event.position().toPoint()
            )
            self.handle_external_drag(event, global_point)
        else:
            super().dropEvent(event)

    def handle_external_drag(self, event, global_point) -> bool:
        """供积木行转发拖放事件。"""
        if not event.mimeData().hasFormat(SNIPPET_MIME):
            return False

        if event.type() == QEvent.Type.Drop:
            payload = bytes(event.mimeData().data(SNIPPET_MIME)).decode(
                "utf-8", errors="replace"
            )
            position = self.viewport().mapFromGlobal(global_point)
            self._insert_from_payload(payload, position)
            event.acceptProposedAction()
            return True

        event.acceptProposedAction()
        return True

    def _insert_from_payload(self, snippet_id: str, position) -> None:
        if snippet_id != EMPTY_KIND:
            try:
                catalog.snippet(snippet_id)
            except KeyError:
                return

        target, where = self._drop_target(position)
        item = self._build_item(self._new_block(snippet_id))
        self._insert_item(item, target, where)
        self._attach_rows(item)
        self.setCurrentItem(item)
        self.scrollToItem(item)
        self.changed.emit()

    def _drop_target(self, position) -> tuple[QTreeWidgetItem | None, str]:
        target = self.itemAt(position)
        if target is None:
            return None, "root"

        rect = self.visualItemRect(target)
        if position.y() < rect.top() + 12:
            return target, "above"
        if position.y() > rect.bottom() - 12:
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

    # ---------------------------------------------------------------- 操作

    def remove_item(self, item: QTreeWidgetItem) -> None:
        parent = item.parent()
        if parent is None:
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))
        else:
            parent.removeChild(item)
        self.changed.emit()

    def _on_current_changed(self, current, previous) -> None:
        for item, selected in ((previous, False), (current, True)):
            if item is None:
                continue
            row = self.itemWidget(item, 0)
            if isinstance(row, BlockRow):
                row.set_selected(selected)

    def _show_menu(self, position) -> None:
        item = self.itemAt(position)
        if item is None:
            return
        self.setCurrentItem(item)
        menu = QMenu(self)
        menu.addAction("删除这块", lambda: self.remove_item(item))
        menu.exec(self.viewport().mapToGlobal(position))

    # ---------------------------------------------------------------- 键盘/尺寸

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Delete:
            item = self.currentItem()
            if item is not None:
                self.remove_item(item)
                return
        super().keyPressEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.setColumnWidth(0, max(240, self.viewport().width() - 4))
