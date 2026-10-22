"""Scratch 风格积木画布：自由定位、容器槽位、拖放。"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRegularExpression, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
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
GRID = 20
CANVAS_SIZE = (2600, 1800)


class BodyArea(QFrame):
    """容器积木里的一个槽位（重复内容 / 那么 / 否则）。"""

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

        self._layout = layout
        self.setStyleSheet(
            "QFrame#blockBody {"
            "  background: rgba(255, 255, 255, 0.55);"
            f" border-left: 3px solid {owner.accent};"
            " border-radius: 4px;"
            "}"
        )

    def add_widget(self, widget: "BlockWidget") -> None:
        self._hint.hide()
        self._layout.addWidget(widget)
        self._widgets.append(widget)
        widget.show()
        self.owner.refresh_size()

    def remove_widget(self, widget: "BlockWidget") -> None:
        if widget in self._widgets:
            self._widgets.remove(widget)
        self._layout.removeWidget(widget)
        if not self._widgets:
            self._hint.show()
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
        self.owner.canvas.add_snippet(payload, body=self)
        event.acceptProposedAction()


class DragHeader(QFrame):
    def __init__(self, owner: "BlockWidget") -> None:
        super().__init__(owner)
        self.owner = owner
        self.setObjectName("blockHeader")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and self.owner.is_top_level():
            self.owner.start_drag(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self.owner.is_dragging:
            self.owner.drag_to(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.owner.is_dragging:
            self.owner.finish_drag()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class BlockWidget(QFrame):
    """画布上的一块积木。"""

    def __init__(self, block: Block, canvas: "BlockCanvas") -> None:
        super().__init__()
        self.block = block
        self.canvas = canvas
        self.snippet = (
            None if block.kind == EMPTY_KIND else catalog.snippet(block.kind)
        )
        self.category = (
            catalog.category(self.snippet.category) if self.snippet else None
        )
        self.accent = self.category.accent if self.category else "#94a3b8"

        self._fields: dict[str, QLineEdit] = {}
        self.bodies: list[BodyArea] = []
        self._dragging = False
        self._drag_offset = QPoint()

        self.setObjectName("blockWidget")
        self.setMinimumWidth(320)
        self.setAcceptDrops(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = DragHeader(self)
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(10, 5, 8, 5)
        header_layout.setSpacing(5)

        if self.snippet is None:
            self._build_empty(header_layout)
        else:
            self._build_snippet(header_layout, self.snippet)

        delete_button = QToolButton(self.header)
        delete_button.setText("✕")
        delete_button.setToolTip("删除这块积木")
        delete_button.setAutoRaise(True)
        delete_button.setFixedSize(22, 22)
        delete_button.clicked.connect(lambda: self.canvas.delete_block(self))
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
                label.setStyleSheet("background: transparent; color: #1f2937;")
                layout.addWidget(label)

        if not has_growing_field:
            layout.addStretch(1)

    # ---------------------------------------------------------------- 数据

    def _on_param_changed(self, name: str, text: str) -> None:
        self.block.params[name] = text
        if self.snippet is not None:
            self.block.text = self.snippet.render(self.block.params)
        self.canvas.changed.emit()

    def _on_code_changed(self, text: str) -> None:
        self.block.text = text
        self.canvas.changed.emit()

    def field(self, name: str) -> QLineEdit | None:
        return self._fields.get(name)

    def code_edit(self) -> QLineEdit | None:
        return self._fields.get("")

    def to_block(self) -> Block:
        children = self.bodies[0].blocks() if self.bodies else []
        else_children = self.bodies[1].blocks() if len(self.bodies) > 1 else []
        top_level = self.is_top_level()
        return Block(
            kind=self.block.kind,
            text=self.block.text,
            params=dict(self.block.params),
            children=children,
            else_children=else_children,
            x=float(self.x()) if top_level else 0.0,
            y=float(self.y()) if top_level else 0.0,
        )

    # ---------------------------------------------------------------- 拖动

    def is_top_level(self) -> bool:
        return self.parent() is self.canvas

    def refresh_size(self) -> None:
        layout = self.layout()
        if layout is not None:
            layout.activate()
        self.adjustSize()
        parent = self.parent()
        if isinstance(parent, BodyArea):
            parent.owner.refresh_size()

    @property
    def is_dragging(self) -> bool:
        return self._dragging

    def start_drag(self, global_position: QPoint) -> None:
        if not self.is_top_level():
            return
        self._drag_offset = global_position - self.mapToGlobal(QPoint(0, 0))
        self._dragging = True
        self.raise_()

    def drag_to(self, global_position: QPoint) -> None:
        if not self._dragging:
            return
        position = self.canvas.mapFromGlobal(global_position - self._drag_offset)
        x = max(0, min(position.x(), self.canvas.width() - self.width()))
        y = max(0, min(position.y(), self.canvas.height() - self.height()))
        self.move(x, y)

    def finish_drag(self) -> None:
        if not self._dragging:
            return
        self._dragging = False
        x = round(self.x() / GRID) * GRID
        y = round(self.y() / GRID) * GRID
        self.move(max(0, x), max(0, y))
        self.canvas.changed.emit()

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
        parent = self.parent()
        if isinstance(parent, BodyArea):
            self.canvas.add_snippet(payload, body=parent)
        elif self.bodies:
            self.canvas.add_snippet(payload, body=self.bodies[0])
        else:
            position = self.canvas.mapFromGlobal(
                event.globalPosition().toPoint()
            ) - QPoint(30, 12)
            self.canvas.add_snippet(payload, pos=position)
        event.acceptProposedAction()

    # ---------------------------------------------------------------- 绘制

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.category.color if self.category else "#f1f5f9"
        painter.setBrush(QColor(color))
        pen = QPen(QColor(self.accent))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        painter.end()


class BlockCanvas(QWidget):
    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(*CANVAS_SIZE)
        self.resize(*CANVAS_SIZE)
        self._top: list[BlockWidget] = []

    # ---------------------------------------------------------------- 增删

    def add_block(
        self,
        block: Block,
        pos: QPoint | None = None,
        body: BodyArea | None = None,
    ) -> BlockWidget:
        widget = BlockWidget(block, self)

        if body is not None:
            body.add_widget(widget)
        else:
            widget.setParent(self)
            widget.show()
            widget.move(pos if pos is not None else self._next_position())
            self._top.append(widget)

        widget.adjustSize()
        return widget

    def add_snippet(
        self,
        snippet_id: str,
        pos: QPoint | None = None,
        body: BodyArea | None = None,
    ) -> BlockWidget:
        block = self._new_block(snippet_id)
        widget = self.add_block(block, pos, body)
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

    def _next_position(self) -> QPoint:
        if not self._top:
            return QPoint(40, 40)
        bottom = max(widget.y() + widget.height() for widget in self._top)
        return QPoint(40, bottom + 16)

    def delete_block(self, widget: BlockWidget) -> None:
        parent = widget.parent()
        if isinstance(parent, BodyArea):
            parent.remove_widget(widget)
        elif widget in self._top:
            self._top.remove(widget)
        widget.deleteLater()
        self.changed.emit()

    # ---------------------------------------------------------------- 读写

    def load_blocks(self, blocks: list[Block]) -> None:
        for widget in self._top:
            widget.deleteLater()
        self._top.clear()

        y = 40
        for block in blocks:
            widget = self._build_widget(block)
            widget.setParent(self)
            widget.show()
            x = int(block.x) if block.x else 40
            top = int(block.y) if block.y else y
            widget.move(x, top)
            self._top.append(widget)
            y = max(y, top + widget.height() + 16)

    def _build_widget(self, block: Block) -> BlockWidget:
        widget = BlockWidget(block, self)
        for index, body in enumerate(widget.bodies):
            children = block.children if index == 0 else block.else_children
            for child in children:
                body.add_widget(self._build_widget(child))
        widget.adjustSize()
        return widget

    def blocks(self) -> list[Block]:
        ordered = sorted(self._top, key=lambda widget: (widget.y(), widget.x()))
        return [widget.to_block() for widget in ordered]

    def showEvent(self, event) -> None:  # noqa: N802
        # 隐藏状态下创建时，布局可能还没有算上子块尺寸，显示后统一重算
        super().showEvent(event)
        for widget in self._top:
            widget.refresh_size()

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
        position = event.position().toPoint() - QPoint(20, 12)
        self.add_snippet(payload, pos=position)
        event.acceptProposedAction()

    # ---------------------------------------------------------------- 绘制

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f7f9fc"))

        pen = QPen(QColor("#e8edf5"))
        pen.setWidth(1)
        painter.setPen(pen)
        for x in range(0, self.width(), GRID):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), GRID):
            painter.drawLine(0, y, self.width(), y)

        if not self._top:
            painter.setPen(QColor("#94a3b8"))
            font = painter.font()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(
                self.rect().adjusted(0, 120, 0, 0),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                "从左侧拖入积木，开始搭建脚本",
            )
        painter.end()


class BlockCanvasView(QScrollArea):
    """带滚动条的画布容器（在 Designer 里提升为这个类）。"""

    changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.canvas = BlockCanvas(self)
        self.setWidget(self.canvas)
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.canvas.resize(*CANVAS_SIZE)
        self.canvas.changed.connect(self.changed.emit)

    def load_blocks(self, blocks: list[Block]) -> None:
        self.canvas.load_blocks(blocks)

    def blocks(self) -> list[Block]:
        return self.canvas.blocks()

    def add_snippet(
        self,
        snippet_id: str,
        pos: QPoint | None = None,
        body: BodyArea | None = None,
    ) -> BlockWidget:
        return self.canvas.add_snippet(snippet_id, pos, body)
