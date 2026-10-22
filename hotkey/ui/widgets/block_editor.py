"""单栏积木编辑器：竖向列表、容器槽位、常驻参数输入框。"""

from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from hotkey.core import catalog
from hotkey.core.models import Block
from hotkey.ui.widgets.statement_tree import SNIPPET_MIME

EMPTY_KIND = "empty"


def body_of(widget: QWidget) -> "BodyArea | None":
    """找到积木所在的槽位（嵌套积木的父级是槽位内部 host）。"""
    parent = widget.parent()
    while parent is not None:
        if isinstance(parent, BodyArea):
            return parent
        parent = parent.parent()
    return None


class BodyArea(QFrame):
    """容器积木里的槽位（函数体 / 那么 / 否则 / 重复内容）。"""

    def __init__(self, owner: "BlockWidget", index: int, label: str) -> None:
        super().__init__(owner)
        self.setObjectName("blockBody")
        self.owner = owner
        self.index = index
        self.setAcceptDrops(True)
        self._widgets: list[BlockWidget] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 6, 10, 10)
        layout.setSpacing(6)
        if label:
            caption = QLabel(label, self)
            caption.setObjectName("bodyLabel")
            layout.addWidget(caption)

        self._hint = QLabel("把积木拖到这里", self)
        self._hint.setObjectName("bodyHint")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint)

        self._host = QWidget(self)
        self._child_layout = QVBoxLayout(self._host)
        self._child_layout.setContentsMargins(0, 0, 0, 0)
        self._child_layout.setSpacing(6)
        layout.addWidget(self._host)

        self.setStyleSheet(
            "QFrame#blockBody {"
            f" border-left: 3px solid {owner.accent};"
            "}"
        )

    @property
    def editor(self):
        return self.owner.editor

    def add_widget(self, widget: "BlockWidget") -> None:
        self._hint.hide()
        self._child_layout.addWidget(widget)
        self._widgets.append(widget)
        widget.show()
        self.owner.refresh_size()

    def insert_after(self, anchor: "BlockWidget", widget: "BlockWidget") -> None:
        index = self._widgets.index(anchor) + 1
        self._widgets.insert(index, widget)
        self._child_layout.insertWidget(index, widget)
        self._hint.hide()
        widget.show()
        self.owner.refresh_size()

    def remove_widget(self, widget: "BlockWidget") -> None:
        if widget in self._widgets:
            self._widgets.remove(widget)
        self._child_layout.removeWidget(widget)
        if not self._widgets:
            self._hint.show()
        self.owner.refresh_size()

    def move_widget(self, widget: "BlockWidget", delta: int) -> None:
        index = self._widgets.index(widget)
        target = index + delta
        if not 0 <= target < len(self._widgets):
            return
        self._widgets[index], self._widgets[target] = (
            self._widgets[target],
            self._widgets[index],
        )
        for child in self._widgets:
            self._child_layout.removeWidget(child)
        for position, child in enumerate(self._widgets):
            self._child_layout.insertWidget(position, child)
        self.owner.refresh_size()

    def blocks(self) -> list[Block]:
        return [widget.to_block() for widget in self._widgets]

    # ---------------------------------------------------------------- 拖放

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        if not event.mimeData().hasFormat(SNIPPET_MIME):
            return
        payload = bytes(event.mimeData().data(SNIPPET_MIME)).decode(
            "utf-8", errors="replace"
        )
        self.editor.add_snippet(payload, body=self)
        event.acceptProposedAction()


class BlockWidget(QFrame):
    """单栏里的一个积木。"""

    def __init__(self, block: Block, editor: "BlockListEditor") -> None:
        super().__init__()
        self.block = block
        self.editor = editor
        self.snippet = (
            None if block.kind == EMPTY_KIND else catalog.snippet(block.kind)
        )
        self.category = (
            catalog.category(self.snippet.category) if self.snippet else None
        )
        self.accent = self.category.accent if self.category else "#94a3b8"

        self._fields: dict[str, QLineEdit] = {}
        self.bodies: list[BodyArea] = []

        self.setObjectName("blockWidget")
        self.setMinimumWidth(320)
        self.setAcceptDrops(True)
        self.setStyleSheet(
            "QFrame#blockWidget {"
            f" border-left: 4px solid {self.accent};"
            "}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = QFrame(self)
        self.header.setObjectName("blockHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 5, 8, 5)
        header_layout.setSpacing(5)

        if self.snippet is None:
            self._build_empty(header_layout)
        else:
            self._build_snippet(header_layout, self.snippet)

        for symbol, delta in (("▲", -1), ("▼", 1)):
            button = QToolButton(self.header)
            button.setText(symbol)
            button.setToolTip("上移" if delta < 0 else "下移")
            button.setAutoRaise(True)
            button.setFixedSize(22, 22)
            button.clicked.connect(
                lambda _checked=False, d=delta: self.editor.move_block(self, d)
            )
            header_layout.addWidget(button)

        delete_button = QToolButton(self.header)
        delete_button.setText("✕")
        delete_button.setToolTip("删除这块积木")
        delete_button.setAutoRaise(True)
        delete_button.setFixedSize(22, 22)
        delete_button.clicked.connect(lambda: self.editor.delete_block(self))
        header_layout.addWidget(delete_button)
        root.addWidget(self.header)

        if self.snippet is not None and self.snippet.block:
            slots = self.snippet.slots or ("内容",)
            for index, label in enumerate(slots):
                body = BodyArea(self, index, label)
                root.addWidget(body)
                self.bodies.append(body)

        self.adjustSize()

    # ---------------------------------------------------------------- 构建

    def _build_empty(self, layout: QHBoxLayout) -> None:
        edit = QLineEdit(self.block.text, self.header)
        edit.setPlaceholderText("在这里写一行 Python 代码")
        edit.setMinimumWidth(220)
        edit.setFixedHeight(28)
        edit.setAcceptDrops(False)
        edit.textChanged.connect(self._on_code_changed)
        layout.addWidget(edit, 1)
        self._fields[""] = edit

    def _build_snippet(
        self, layout: QHBoxLayout, snippet: catalog.Snippet
    ) -> None:
        has_growing_field = False

        for segment in snippet.segments():
            if isinstance(segment, catalog.Param):
                edit = QLineEdit(self.block.params.get(segment.name, ""), self.header)
                edit.setPlaceholderText(segment.placeholder)
                edit.setFixedHeight(26)
                edit.setAcceptDrops(False)

                if segment.kind in ("number", "code"):
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
                label = QLabel(segment, self.header)
                layout.addWidget(label)

        if not has_growing_field:
            layout.addStretch(1)

    # ---------------------------------------------------------------- 数据

    def _on_param_changed(self, name: str, text: str) -> None:
        self.block.params[name] = text
        if self.snippet is not None:
            self.block.text = self.snippet.render(self.block.params)
        self.editor.changed.emit()

    def _on_code_changed(self, text: str) -> None:
        self.block.text = text
        self.editor.changed.emit()

    def field(self, name: str) -> QLineEdit | None:
        return self._fields.get(name)

    def code_edit(self) -> QLineEdit | None:
        return self._fields.get("")

    def to_block(self) -> Block:
        children = self.bodies[0].blocks() if self.bodies else []
        else_children = self.bodies[1].blocks() if len(self.bodies) > 1 else []
        return Block(
            kind=self.block.kind,
            text=self.block.text,
            params=dict(self.block.params),
            children=children,
            else_children=else_children,
        )

    def refresh_size(self) -> None:
        layout = self.layout()
        if layout is not None:
            layout.activate()
        self.adjustSize()
        body = body_of(self)
        if body is not None:
            body.owner.refresh_size()

    # ---------------------------------------------------------------- 拖放

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        if not event.mimeData().hasFormat(SNIPPET_MIME):
            return
        payload = bytes(event.mimeData().data(SNIPPET_MIME)).decode(
            "utf-8", errors="replace"
        )
        self.editor.add_snippet(payload, after=self)
        event.acceptProposedAction()


class _DropHost(QWidget):
    def __init__(self, editor: "BlockListEditor") -> None:
        super().__init__()
        self.editor = editor
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        if not event.mimeData().hasFormat(SNIPPET_MIME):
            return
        payload = bytes(event.mimeData().data(SNIPPET_MIME)).decode(
            "utf-8", errors="replace"
        )
        self.editor.add_snippet(payload)
        event.acceptProposedAction()


class BlockListEditor(QScrollArea):
    """单栏积木列表（在 Designer 里提升为这个类）。"""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._host = _DropHost(self)
        self._layout = QVBoxLayout(self._host)
        self._layout.setContentsMargins(10, 10, 10, 10)
        self._layout.setSpacing(8)
        self._layout.addStretch(1)
        self._blocks: list[BlockWidget] = []

        self.setWidget(self._host)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    # ---------------------------------------------------------------- 增删

    def add_block(
        self,
        block: Block,
        body: BodyArea | None = None,
        after: BlockWidget | None = None,
    ) -> BlockWidget:
        widget = BlockWidget(block, self)

        if body is not None:
            body.add_widget(widget)
        elif after is not None:
            owning = body_of(after)
            if owning is not None:
                owning.insert_after(after, widget)
            elif after in self._blocks:
                index = self._blocks.index(after) + 1
                self._blocks.insert(index, widget)
                self._attach_top(widget)
                self._relayout()
        else:
            self._blocks.append(widget)
            self._attach_top(widget)
            self._relayout()

        widget.adjustSize()
        widget.refresh_size()
        return widget

    def _attach_top(self, widget: BlockWidget) -> None:
        widget.setParent(self._host)
        widget.show()

    def _relayout(self) -> None:
        for widget in self._blocks:
            self._layout.removeWidget(widget)
        for index, widget in enumerate(self._blocks):
            self._layout.insertWidget(index, widget)

    def add_snippet(
        self,
        snippet_id: str,
        body: BodyArea | None = None,
        after: BlockWidget | None = None,
    ) -> BlockWidget:
        block = self._new_block(snippet_id)
        widget = self.add_block(block, body, after)
        self.changed.emit()
        return widget

    def _new_block(self, snippet_id: str) -> Block:
        if snippet_id == EMPTY_KIND:
            return Block(kind=EMPTY_KIND, text="")
        snippet = catalog.snippet(snippet_id)
        params = snippet.blank_values()
        return Block(
            kind=snippet_id,
            text=snippet.render(params),
            params=params,
        )

    def delete_block(self, widget: BlockWidget) -> None:
        owning = body_of(widget)
        if owning is not None:
            owning.remove_widget(widget)
        elif widget in self._blocks:
            self._blocks.remove(widget)
        widget.deleteLater()
        self._relayout()
        self.changed.emit()

    def move_block(self, widget: BlockWidget, delta: int) -> None:
        owning = body_of(widget)
        if owning is not None:
            owning.move_widget(widget, delta)
            self.changed.emit()
            return

        if widget not in self._blocks:
            return
        index = self._blocks.index(widget)
        target = index + delta
        if not 0 <= target < len(self._blocks):
            return
        self._blocks[index], self._blocks[target] = (
            self._blocks[target],
            self._blocks[index],
        )
        self._relayout()
        self.changed.emit()

    # ---------------------------------------------------------------- 读写

    def load_blocks(self, blocks: list[Block]) -> None:
        for widget in self._blocks:
            self._layout.removeWidget(widget)
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        self._blocks.clear()

        for block in blocks:
            widget = self._build_widget(block)
            self._blocks.append(widget)
            self._attach_top(widget)
        self._relayout()

        for widget in self._blocks:
            widget.refresh_size()

    def _build_widget(self, block: Block) -> BlockWidget:
        widget = BlockWidget(block, self)
        for index, body in enumerate(widget.bodies):
            children = block.children if index == 0 else block.else_children
            for child in children:
                body.add_widget(self._build_widget(child))
        widget.adjustSize()
        return widget

    def blocks(self) -> list[Block]:
        return [widget.to_block() for widget in self._blocks]

    def clear(self) -> None:
        for widget in self._blocks:
            widget.deleteLater()
        self._blocks.clear()

    def dropEvent(self, event) -> None:  # noqa: N802
        if not event.mimeData().hasFormat(SNIPPET_MIME):
            return
        payload = bytes(event.mimeData().data(SNIPPET_MIME)).decode(
            "utf-8", errors="replace"
        )
        self.add_snippet(payload)
        event.acceptProposedAction()
