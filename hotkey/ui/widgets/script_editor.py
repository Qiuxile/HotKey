"""脚本编辑器控件（在 Designer 里由 QPlainTextEdit 提升而来）。"""

from __future__ import annotations

from PySide6.QtGui import QFontDatabase, QFontMetrics
from PySide6.QtWidgets import QPlainTextEdit


class ScriptEditor(QPlainTextEdit):
    """M3 会在这里加入自动缩进、语法高亮与拖放插入。"""

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
