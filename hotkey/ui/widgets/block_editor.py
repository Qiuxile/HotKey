"""单栏积木编辑器：竖向列表、容器槽位、常驻参数输入框。"""

from __future__ import annotations

from uuid import uuid4

from PySide6.QtCore import QEvent, QMimeData, QRegularExpression, Qt, Signal
from PySide6.QtGui import QDrag, QKeySequence, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from hotkey.core import catalog, keymap
from hotkey.core.blocks import expression_code, literal_code
from hotkey.core.models import Block
from hotkey.ui.widgets.statement_tree import SNIPPET_MIME

EMPTY_KIND = "empty"
BLOCK_MOVE_MIME = "application/x-hotkey-block-move"


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
        self.arrange()

    def arrange(self) -> None:
        for child in self._widgets:
            self._child_layout.removeWidget(child)
        for position, child in enumerate(self._widgets):
            self._child_layout.insertWidget(position, child)
        self.owner.refresh_size()

    def move_to_end(self, widget: "BlockWidget") -> None:
        if widget not in self._widgets:
            return
        self._widgets.remove(widget)
        self._widgets.append(widget)
        self.arrange()
        self.editor.changed.emit()

    def blocks(self) -> list[Block]:
        return [widget.to_block() for widget in self._widgets]

    # ---------------------------------------------------------------- 拖放

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME) or event.mimeData().hasFormat(
            BLOCK_MOVE_MIME
        ):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME) or event.mimeData().hasFormat(
            BLOCK_MOVE_MIME
        ):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(BLOCK_MOVE_MIME):
            token = bytes(event.mimeData().data(BLOCK_MOVE_MIME)).decode(
                "utf-8", errors="replace"
            )
            source = self.editor.source_for(token)
            if source is not None and body_of(source) is self:
                self.move_to_end(source)
            event.acceptProposedAction()
            return
        if event.mimeData().hasFormat(SNIPPET_MIME):
            payload = bytes(event.mimeData().data(SNIPPET_MIME)).decode(
                "utf-8", errors="replace"
            )
            self.editor.add_snippet(payload, body=self)
            event.acceptProposedAction()


class _DragHandle(QLabel):
    """积木左侧的拖拽手柄，只有按住它才会开始排序拖拽。"""

    def __init__(self, block: "BlockWidget") -> None:
        super().__init__("≡", block.header)
        self._block = block
        self._press_pos = None
        self.setObjectName("blockDragHandle")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(16)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("拖动这里调整顺序")

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.position().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if (
            self._press_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and (event.position().toPoint() - self._press_pos).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._press_pos = None
            self._block.start_reorder_drag()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._press_pos = None
        super().mouseReleaseEvent(event)


class KeyCapture(QPushButton):
    """点击后直接按实体键盘，显示捕获到的键。"""

    changed = Signal(str)

    def __init__(self, mode: str, value: str = "", parent=None) -> None:
        super().__init__(parent)
        self._mode = mode
        self._value = value
        self._capturing = False
        self.setObjectName("keyCapture")
        self.setFixedHeight(26)
        self.setMinimumWidth(130)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("点击后直接按实体键盘；按 Esc 取消")
        self.clicked.connect(self.start_capture)
        self._refresh()

    def value(self) -> str:
        return self._value

    def set_value(self, value: str) -> None:
        self._value = value
        self._refresh()

    def _refresh(self) -> None:
        if self._value:
            self.setText(keymap.keyboard_to_qt(self._value))
        else:
            self.setText("点击后按键" if self._mode == "key" else "点击后组合键")

    def start_capture(self) -> None:
        self._capturing = True
        self.setText("请按键盘…")
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        self.grabKeyboard()

    def cancel_capture(self) -> None:
        if self._capturing:
            self._capturing = False
            self.releaseKeyboard()
            self._refresh()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if not self._capturing:
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_capture()
            event.accept()
            return
        if event.key() in (
            Qt.Key.Key_Control,
            Qt.Key.Key_Shift,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
        ):
            return
        sequence = QKeySequence(event.keyCombination()).toString(
            QKeySequence.SequenceFormat.PortableText
        )
        converted = keymap.qt_to_keyboard(sequence)
        if converted is None or keymap.is_modifier_only(converted):
            return
        if self._mode == "key" and "+" in converted:
            self.setText("请只按一个键…")
            return

        self._value = converted
        self._capturing = False
        self.releaseKeyboard()
        self._refresh()
        self.changed.emit(self._value)
        event.accept()

    def focusOutEvent(self, event) -> None:  # noqa: N802
        self.cancel_capture()
        super().focusOutEvent(event)


class BlockWidget(QFrame):
    """单栏里的一个积木；``compact`` 时作为值槽里的表达式片段。"""

    def __init__(
        self,
        block: Block,
        editor: "BlockListEditor",
        *,
        compact: bool = False,
    ) -> None:
        super().__init__()
        self.block = block
        self.editor = editor
        self.compact = compact
        self.snippet = (
            None if block.kind == EMPTY_KIND else catalog.snippet(block.kind)
        )
        self.category = (
            catalog.category(self.snippet.category) if self.snippet else None
        )
        self.accent = self.category.accent if self.category else "#94a3b8"

        self._fields: dict[str, QLineEdit] = {}
        self._value_slots: dict[str, ValueSlot] = {}
        self._key_fields: dict[str, KeyCapture] = {}
        self.bodies: list[BodyArea] = []

        self.setObjectName("blockWidget")
        self.setProperty("compact", compact)
        self.setMinimumWidth(0 if compact else 320)
        self.setAcceptDrops(True)
        self.setStyleSheet(
            "QFrame#blockWidget {"
            f" border-left: {3 if compact else 4}px solid {self.accent};"
            "}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.header = QFrame(self)
        self.header.setObjectName("blockHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(4 if compact else 6, 3 if compact else 5, 4 if compact else 8, 3 if compact else 5)
        header_layout.setSpacing(4 if compact else 5)

        self.drag_handle = None if compact else _DragHandle(self)
        if self.drag_handle is not None:
            header_layout.addWidget(self.drag_handle)

        if self.snippet is None:
            self._build_empty(header_layout)
        else:
            self._build_snippet(header_layout, self.snippet)

        if not compact:
            delete_button = QToolButton(self.header)
            delete_button.setText("✕")
            delete_button.setToolTip("删除这块积木")
            delete_button.setAutoRaise(True)
            delete_button.setFixedSize(22, 22)
            delete_button.clicked.connect(lambda: self.editor.delete_block(self))
            header_layout.addWidget(delete_button)
        root.addWidget(self.header)

        if not compact and self.snippet is not None and self.snippet.block:
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
                if segment.kind == "value":
                    slot = ValueSlot(self, segment)
                    layout.addWidget(slot, 1)
                    slot.changed.connect(self.editor.changed.emit)
                    self._value_slots[segment.name] = slot
                    has_growing_field = True
                    continue

                if segment.kind in ("key", "hotkey"):
                    key_field = KeyCapture(
                        segment.kind,
                        self.block.params.get(segment.name, ""),
                        self.header,
                    )
                    key_field.changed.connect(
                        lambda text, name=segment.name: self._on_param_changed(
                            name, text
                        )
                    )
                    layout.addWidget(key_field, 1)
                    self._key_fields[segment.name] = key_field
                    has_growing_field = True
                    continue

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

    def value_slot(self, name: str) -> "ValueSlot | None":
        return self._value_slots.get(name)

    def key_field(self, name: str) -> KeyCapture | None:
        return self._key_fields.get(name)

    def code_edit(self) -> QLineEdit | None:
        return self._fields.get("")

    def to_block(self) -> Block:
        children = self.bodies[0].blocks() if self.bodies else []
        else_children = self.bodies[1].blocks() if len(self.bodies) > 1 else []
        params = dict(self.block.params)
        expressions: dict[str, Block] = {}
        value_modes: dict[str, str] = {}
        for name, slot in self._value_slots.items():
            params[name] = slot.literal
            value_modes[name] = slot.mode
            expression = slot.to_expression()
            if expression is not None:
                expressions[name] = expression
        return Block(
            kind=self.block.kind,
            text=self.block.text,
            params=params,
            children=children,
            else_children=else_children,
            expressions=expressions,
            value_modes=value_modes,
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

    def start_reorder_drag(self) -> None:
        token = self.editor.begin_block_drag(self)
        mime = QMimeData()
        mime.setData(BLOCK_MOVE_MIME, token.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = self.grab()
        if not pixmap.isNull():
            drag.setPixmap(
                pixmap.scaledToWidth(
                    min(520, pixmap.width()),
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        drag.exec(Qt.DropAction.MoveAction)
        self.editor.end_block_drag(token)

    def _set_drop_hint(self, after: bool | None) -> None:
        value = "" if after is None else ("after" if after else "before")
        self.setProperty("dropPosition", value)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME) or self._has_move(event):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if self._has_move(event):
            self._set_drop_hint(event.position().y() > self.height() / 2)
            event.acceptProposedAction()
        elif event.mimeData().hasFormat(SNIPPET_MIME):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._set_drop_hint(None)
        super().dragLeaveEvent(event)

    def _has_move(self, event) -> bool:
        return event.mimeData().hasFormat(BLOCK_MOVE_MIME)

    def dropEvent(self, event) -> None:  # noqa: N802
        self._set_drop_hint(None)
        if self._has_move(event):
            token = bytes(event.mimeData().data(BLOCK_MOVE_MIME)).decode(
                "utf-8", errors="replace"
            )
            source = self.editor.source_for(token)
            if source is not None:
                after = event.position().y() > self.height() / 2
                self.editor.reorder_block(source, self, after)
            event.acceptProposedAction()
            return
        if event.mimeData().hasFormat(SNIPPET_MIME):
            payload = bytes(event.mimeData().data(SNIPPET_MIME)).decode(
                "utf-8", errors="replace"
            )
            self.editor.add_snippet(payload, after=self)
            event.acceptProposedAction()


class ValueSlot(QFrame):
    """值槽：可手填字面量，也可拖入一个有返回值的表达式积木。"""

    changed = Signal()
    MODES = (
        ("自动", "auto"),
        ("文本", "text"),
        ("数字", "number"),
        ("布尔", "bool"),
        ("代码", "code"),
    )

    def __init__(self, owner: "BlockWidget", param: catalog.Param) -> None:
        super().__init__(owner.header)
        self.owner = owner
        self.editor = owner.editor
        self.param = param
        self.literal = owner.block.params.get(param.name, "")
        self.mode = owner.block.value_modes.get(param.name, param.mode)
        self.expression: Block | None = None
        self._expression_widget: BlockWidget | None = None

        self.setObjectName("valueSlot")
        self.setAcceptDrops(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.setSpacing(3)
        self._layout = layout

        self.mode_combo = QComboBox(self)
        self.mode_combo.setObjectName("valueMode")
        self.mode_combo.setFixedWidth(48)
        for label, value in self.MODES:
            self.mode_combo.addItem(label, value)
        index = max(0, self.mode_combo.findData(self.mode))
        self.mode_combo.setCurrentIndex(index)
        self.mode_combo.setToolTip("手填值的类型；拖入表达式积木后自动忽略")
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo)

        self.edit = QLineEdit(self.literal, self)
        self.edit.setPlaceholderText(param.placeholder or "值")
        self.edit.setFixedHeight(22)
        self.edit.setAcceptDrops(False)
        self.edit.textChanged.connect(self._on_literal_changed)
        self.edit.installEventFilter(self)
        layout.addWidget(self.edit, 1)

        self.clear_button = QToolButton(self)
        self.clear_button.setText("✕")
        self.clear_button.setAutoRaise(True)
        self.clear_button.setFixedSize(18, 18)
        self.clear_button.setToolTip("清除表达式，改回手填")
        self.clear_button.hide()
        self.clear_button.clicked.connect(self.clear_expression)
        layout.addWidget(self.clear_button)

        expression = owner.block.expressions.get(param.name)
        if expression is not None:
            self.set_expression(expression)

    # ---------------------------------------------------------------- 手填

    def _on_literal_changed(self, text: str) -> None:
        self.literal = text
        self.changed.emit()

    def _on_mode_changed(self, _index: int) -> None:
        self.mode = self.mode_combo.currentData() or "auto"
        self.changed.emit()

    def code(self) -> str:
        if self.expression is not None:
            expression = self.to_expression()
            return expression_code(expression)
        return literal_code(self.literal, self.mode)

    def to_expression(self) -> Block | None:
        if self._expression_widget is not None:
            return self._expression_widget.to_block()
        return self.expression

    def expression_widget(self) -> "BlockWidget | None":
        return self._expression_widget

    # ---------------------------------------------------------------- 表达式

    def set_expression(self, block: Block) -> None:
        self.expression = block
        self._remove_expression_widget()
        widget = BlockWidget(block, self.editor, compact=True)
        self._expression_widget = widget
        self._layout.insertWidget(1, widget)
        widget.show()
        self.edit.hide()
        self.mode_combo.hide()
        self.clear_button.show()
        self.changed.emit()

    def clear_expression(self, *_args) -> None:
        if self.expression is None:
            return
        self.expression = None
        self._remove_expression_widget()
        self.edit.show()
        self.mode_combo.show()
        self.clear_button.hide()
        self.changed.emit()

    def _remove_expression_widget(self) -> None:
        if self._expression_widget is not None:
            self._layout.removeWidget(self._expression_widget)
            self._expression_widget.hide()
            self._expression_widget.setParent(None)
            self._expression_widget.deleteLater()
            self._expression_widget = None

    # ---------------------------------------------------------------- 拖放

    def _accepted_snippet(self, event) -> catalog.Snippet | None:
        if not event.mimeData().hasFormat(SNIPPET_MIME):
            return None
        snippet_id = bytes(event.mimeData().data(SNIPPET_MIME)).decode(
            "utf-8", errors="replace"
        )
        try:
            snippet = catalog.snippet(snippet_id)
        except KeyError:
            return None
        return snippet if snippet.expression else None

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        # QLineEdit 不接受拖放；把落在输入框上的拖放转给值槽
        if watched is self.edit and event.type() in (
            QEvent.Type.DragEnter,
            QEvent.Type.DragMove,
            QEvent.Type.Drop,
        ):
            if event.type() == QEvent.Type.Drop:
                self.dropEvent(event)
            elif event.type() == QEvent.Type.DragEnter:
                self.dragEnterEvent(event)
            else:
                self.dragMoveEvent(event)
            return True
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if self._accepted_snippet(event) is not None:
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if self._accepted_snippet(event) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        snippet = self._accepted_snippet(event)
        if snippet is None:
            return
        params = snippet.blank_values()
        block = Block(
            kind=snippet.id,
            text=snippet.render(params),
            params=params,
        )
        self.set_expression(block)
        event.acceptProposedAction()


class _DropHost(QWidget):
    def __init__(self, editor: "BlockListEditor") -> None:
        super().__init__()
        self.editor = editor
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME) or event.mimeData().hasFormat(
            BLOCK_MOVE_MIME
        ):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(SNIPPET_MIME) or event.mimeData().hasFormat(
            BLOCK_MOVE_MIME
        ):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasFormat(BLOCK_MOVE_MIME):
            token = bytes(event.mimeData().data(BLOCK_MOVE_MIME)).decode(
                "utf-8", errors="replace"
            )
            source = self.editor.source_for(token)
            if source is not None:
                self.editor.move_to_end(source)
            event.acceptProposedAction()
            return
        if event.mimeData().hasFormat(SNIPPET_MIME):
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
        self._drag_sources: dict[str, BlockWidget] = {}

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

    # ---------------------------------------------------------------- 拖拽排序

    def begin_block_drag(self, widget: BlockWidget) -> str:
        token = uuid4().hex
        self._drag_sources[token] = widget
        return token

    def end_block_drag(self, token: str) -> None:
        self._drag_sources.pop(token, None)

    def source_for(self, token: str) -> BlockWidget | None:
        return self._drag_sources.get(token)

    def reorder_block(
        self, source: BlockWidget, target: BlockWidget, after: bool
    ) -> None:
        """在同一层（顶层或同一个槽位）内把 source 移到 target 前/后。"""
        source_body = body_of(source)
        target_body = body_of(target)
        if source_body is not target_body or source is target:
            return

        widgets = source_body._widgets if source_body else self._blocks
        if source not in widgets or target not in widgets:
            return

        widgets.remove(source)
        index = widgets.index(target) + (1 if after else 0)
        widgets.insert(index, source)
        if source_body is not None:
            source_body.arrange()
        else:
            self._relayout()
        self.changed.emit()

    def move_to_end(self, widget: BlockWidget) -> None:
        if body_of(widget) is not None or widget not in self._blocks:
            return
        if self._blocks and self._blocks[-1] is widget:
            return
        self._blocks.remove(widget)
        self._blocks.append(widget)
        self._relayout()
        self.changed.emit()

    def add_snippet(
        self,
        snippet_id: str,
        body: BodyArea | None = None,
        after: BlockWidget | None = None,
    ) -> BlockWidget | None:
        if snippet_id != EMPTY_KIND:
            snippet = catalog.snippet(snippet_id)
            if not snippet.statement:
                return None
            if snippet_id == "flow_elif":
                target_body = body
                if target_body is None and after is not None:
                    target_body = body_of(after)
                if target_body is None or target_body.index != 1:
                    return None
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
