"""脚本编辑器的简易 Python 语法高亮。"""

from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


def _format(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


class PythonHighlighter(QSyntaxHighlighter):
    KEYWORDS = (
        "and", "as", "assert", "break", "class", "continue", "def", "del",
        "elif", "else", "except", "finally", "for", "from", "global", "if",
        "import", "in", "is", "lambda", "not", "or", "pass", "raise",
        "return", "try", "while", "with", "yield",
    )
    CONSTANTS = ("True", "False", "None")

    def __init__(self, document) -> None:
        super().__init__(document)
        keyword_format = _format("#c792ea", bold=True)
        constant_format = _format("#f78c6c")
        string_format = _format("#c3e88d")
        comment_format = _format("#637777", italic=True)
        number_format = _format("#f78c6c")

        self._rules = [
            (
                QRegularExpression(r"\b(" + "|".join(self.KEYWORDS) + r")\b"),
                keyword_format,
            ),
            (
                QRegularExpression(r"\b(" + "|".join(self.CONSTANTS) + r")\b"),
                constant_format,
            ),
            (QRegularExpression(r"#[^\n]*"), comment_format),
            (QRegularExpression(r"'[^'\\]*(?:\\.[^'\\]*)*'"), string_format),
            (QRegularExpression(r'"[^"\\]*(?:\\.[^"\\]*)*"'), string_format),
            (QRegularExpression(r"\b\d+(?:\.\d+)?\b"), number_format),
        ]

    def highlightBlock(self, text: str) -> None:  # noqa: N802 - Qt 接口
        for regex, fmt in self._rules:
            iterator = regex.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(
                    match.capturedStart(), match.capturedLength(), fmt
                )
