"""脚本编辑器的拖放插入与自动缩进测试。"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from hotkey.core import catalog
from hotkey.ui.widgets.script_editor import ScriptEditor


def make_editor(qtbot):
    editor = ScriptEditor()
    qtbot.addWidget(editor)
    return editor


def move_cursor_to_end(editor):
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    editor.setTextCursor(cursor)


def test_insert_block_snippet(qtbot):
    editor = make_editor(qtbot)

    editor.insert_snippet(catalog.snippet("flow_for_3"))

    assert editor.toPlainText() == "for i in range(3):\n    "
    assert editor.textCursor().position() == len(editor.toPlainText())


def test_insert_block_snippet_inside_indent(qtbot):
    editor = make_editor(qtbot)
    editor.setPlainText("    ")
    move_cursor_to_end(editor)

    editor.insert_snippet(catalog.snippet("flow_for_3"))

    assert editor.toPlainText() == "    for i in range(3):\n        "
    assert editor.textCursor().position() == len(editor.toPlainText())


def test_insert_inline_snippet(qtbot):
    editor = make_editor(qtbot)

    editor.insert_snippet(catalog.snippet("mouse_click"))

    assert editor.toPlainText() == "pyautogui.click()"


def test_return_keeps_indent_and_opens_block(qtbot):
    editor = make_editor(qtbot)
    editor.setPlainText("if True:")
    move_cursor_to_end(editor)

    qtbot.keyPress(editor, Qt.Key.Key_Return)

    assert editor.toPlainText() == "if True:\n    "


def test_tab_inserts_four_spaces(qtbot):
    editor = make_editor(qtbot)

    qtbot.keyPress(editor, Qt.Key.Key_Tab)

    assert editor.toPlainText() == "    "


def test_backspace_dedents_indent(qtbot):
    editor = make_editor(qtbot)
    editor.setPlainText("        x = 1")
    cursor = editor.textCursor()
    cursor.setPosition(8)
    editor.setTextCursor(cursor)

    qtbot.keyPress(editor, Qt.Key.Key_Backspace)

    assert editor.toPlainText() == "    x = 1"
