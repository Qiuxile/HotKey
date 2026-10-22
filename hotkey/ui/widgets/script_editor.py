"""脚本编辑器：拖放语句、自动缩进、语法高亮。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase, QFontMetrics
from PySide6.QtWidgets import QPlainTextEdit

from hotkey.core import catalog
from hotkey.ui.widgets.highlighter import PythonHighlighter
from hotkey.ui.widgets.statement_tree import SNIPPET_MIME


class ScriptEditor(QPlainTextEdit):
    TAB_WIDTH = 4

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setPointSize(10)
        self.setFont(font)
        self.setTabStopDistance(
            QFontMetrics(font).horizontalAdvance(" ") * self.TAB_WIDTH
        )
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setPlaceholderText("从左侧操作面板拖入语句，或直接输入 Python 代码")
        self.setAcceptDrops(True)
        self._highlighter = PythonHighlighter(self.document())

    # ---------------------------------------------------------------- 插入语句

    def _leading_indent(self) -> str:
        line = self.textCursor().block().text()
        return line[: len(line) - len(line.lstrip())]

    def insert_snippet(self, snippet: catalog.Snippet) -> None:
        text, offset = snippet.render()
        cursor = self.textCursor()
        start = cursor.position()
        indent = self._leading_indent()

        inserted = text
        if "\n" in text:
            head, *rest = text.split("\n")
            rest = [indent + line if line else line for line in rest]
            inserted = "\n".join([head, *rest])

        cursor.insertText(inserted)

        if offset is not None:
            line_index = text[:offset].count("\n")
            delta = offset + line_index * len(indent)
            cursor.setPosition(start + delta)
            self.setTextCursor(cursor)

        self.setFocus()

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
        payload = bytes(mime.data(SNIPPET_MIME)).decode("utf-8", errors="replace")
        try:
            snippet = catalog.snippet(payload)
        except KeyError:
            event.ignore()
            return

        self.setTextCursor(self.cursorForPosition(event.position().toPoint()))
        self.insert_snippet(snippet)
        event.acceptProposedAction()

    # ---------------------------------------------------------------- 缩进

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not self.textCursor().hasSelection():
                cursor = self.textCursor()
                line = cursor.block().text()
                indent = line[: len(line) - len(line.lstrip())]
                extra = catalog.INDENT if line.rstrip().endswith(":") else ""
                cursor.insertText("\n" + indent + extra)
                self.setTextCursor(cursor)
                return

        if event.key() == Qt.Key.Key_Tab:
            self.textCursor().insertText(catalog.INDENT)
            return

        if event.key() == Qt.Key.Key_Backspace:
            cursor = self.textCursor()
            if not cursor.hasSelection():
                line = cursor.block().text()
                before = line[: cursor.positionInBlock()]
                if (
                    before
                    and not before.strip()
                    and len(before) % len(catalog.INDENT) == 0
                ):
                    for _ in range(len(catalog.INDENT)):
                        cursor.deletePreviousChar()
                    self.setTextCursor(cursor)
                    return

        super().keyPressEvent(event)
