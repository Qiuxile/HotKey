"""语言层：值槽、变量、条件、循环与函数返回值。"""

from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QDropEvent

from hotkey.core import blocks as codegen, catalog
from hotkey.core.models import Block
from hotkey.ui.widgets.block_editor import BlockListEditor, SNIPPET_MIME


def make_editor(qtbot):
    editor = BlockListEditor()
    qtbot.addWidget(editor)
    editor.resize(800, 600)
    return editor


def test_value_slot_literal_modes(qtbot):
    editor = make_editor(qtbot)
    assign = editor.add_snippet("logic_set")
    assign.field("name").setText("message")

    slot = assign.value_slot("value")
    assert slot is not None

    slot.mode_combo.setCurrentIndex(slot.mode_combo.findData("auto"))
    slot.edit.setText("hello")
    assert codegen.blocks_to_code(editor.blocks()) == "message = 'hello'"

    slot.mode_combo.setCurrentIndex(slot.mode_combo.findData("number"))
    slot.edit.setText("42")
    assert codegen.blocks_to_code(editor.blocks()) == "message = 42"

    slot.mode_combo.setCurrentIndex(slot.mode_combo.findData("bool"))
    slot.edit.setText("是")
    assert codegen.blocks_to_code(editor.blocks()) == "message = True"


def test_value_slot_accepts_return_value_expression(qtbot):
    editor = make_editor(qtbot)
    assign = editor.add_snippet("logic_set")
    assign.field("name").setText("result")
    slot = assign.value_slot("value")
    assert slot is not None

    slot.set_expression(
        Block(
            "value_func_call",
            params={"name": "find_and_click", "args": "image, 3"},
        )
    )

    assert codegen.blocks_to_code(editor.blocks()) == (
        "result = find_and_click(image, 3)"
    )


def test_value_slot_accepts_dropped_value_block(qtbot):
    editor = make_editor(qtbot)
    assign = editor.add_snippet("logic_set")
    assign.field("name").setText("result")
    slot = assign.value_slot("value")
    assert slot is not None

    mime = QMimeData()
    mime.setData(SNIPPET_MIME, b"value_variable")
    event = QDropEvent(
        QPointF(0, 0),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    slot.dropEvent(event)

    assert slot.expression is not None
    assert slot.expression.kind == "value_variable"

    # 表达式积木不能被当成普通语句加到积木栏
    assert editor.add_snippet("value_compare") is None


def test_if_elif_else_codegen():
    tree = Block(
        "flow_if_else",
        params={"condition": "x > 0"},
        value_modes={"condition": "code"},
        children=[Block("mouse_click")],
        else_children=[
            Block(
                "flow_elif",
                params={"condition": "x == 0"},
                value_modes={"condition": "code"},
                children=[Block("key_press_enter")],
                else_children=[Block("key_type_text", params={"text": "no"})],
            )
        ],
    )

    assert codegen.blocks_to_code([tree]) == (
        "if x > 0:\n"
        "    pyautogui.click()\n"
        "elif x == 0:\n"
        "    pyautogui.press('enter')\n"
        "else:\n"
        "    pyautogui.typewrite('no')"
    )


def test_while_and_for_range_codegen():
    while_loop = Block(
        "flow_while",
        params={"condition": "count < 3"},
        value_modes={"condition": "code"},
        children=[Block("logic_change", params={"name": "count", "value": "1"}, value_modes={"value": "number"})],
    )
    for_loop = Block(
        "flow_for_range",
        params={"name": "i", "start": "0", "end": "3", "step": "1"},
        children=[Block("mouse_click")],
    )

    code = codegen.blocks_to_code([while_loop, for_loop])
    assert "while count < 3:" in code
    assert "count += 1" in code
    assert "for i in range(0, 3, 1):" in code


def test_function_assignments_are_global():
    function = Block(
        "logic_func_def",
        params={"name": "set_flag", "params": "value"},
        children=[
            Block("logic_set", params={"name": "flag", "value": "True"}, value_modes={"value": "bool"}),
            Block("logic_set", params={"name": "value", "value": "1"}, value_modes={"value": "number"}),
        ],
    )

    code = codegen.blocks_to_code([function])
    assert "global flag" in code
    assert "global value" not in code


def test_wait_block_has_parameter():
    wait = Block("flow_wait", params={"seconds": "0.5"})
    assert codegen.blocks_to_code([wait]) == "time.sleep(0.5)"


def test_dialog_prompt_returns_input_value():
    snippet = catalog.snippet("value_prompt")
    assert snippet.expression is True
    assert snippet.code_for_values({"text": "名字"}) == "pyautogui.prompt('名字')"
