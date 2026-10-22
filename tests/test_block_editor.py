"""单栏积木编辑器：参数、顺序、容器、判断、删除。"""

from hotkey.core import blocks as block_ops
from hotkey.core.models import Block
from hotkey.ui.widgets.block_editor import BlockListEditor, BlockWidget


def make_editor(qtbot):
    editor = BlockListEditor()
    qtbot.addWidget(editor)
    editor.resize(700, 600)
    editor.show()
    return editor


def test_add_snippet_and_fill_params(qtbot):
    editor = make_editor(qtbot)
    widget = editor.add_snippet("mouse_move_to")

    assert isinstance(widget, BlockWidget)
    widget.field("x").setText("800")
    widget.field("y").setText("600")

    blocks = editor.blocks()
    assert blocks[0].params == {"x": "800", "y": "600"}
    assert block_ops.blocks_to_code(blocks) == "pyautogui.moveTo(800, 600)"


def test_order_and_move(qtbot):
    editor = make_editor(qtbot)
    first = editor.add_snippet("mouse_click")
    second = editor.add_snippet("mouse_double_click")
    third = editor.add_snippet("mouse_right_click")

    editor.move_block(third, -1)
    assert [block.kind for block in editor.blocks()] == [
        "mouse_click",
        "mouse_right_click",
        "mouse_double_click",
    ]

    editor.move_block(first, 1)
    assert [block.kind for block in editor.blocks()] == [
        "mouse_right_click",
        "mouse_click",
        "mouse_double_click",
    ]


def test_container_holds_children(qtbot):
    editor = make_editor(qtbot)
    loop = editor.add_snippet("flow_for_3")
    editor.add_snippet("mouse_click", body=loop.bodies[0])

    assert loop.height() > loop.header.height()
    assert block_ops.blocks_to_code(editor.blocks()) == (
        "for i in range(3):\n    pyautogui.click()"
    )


def test_if_else_branches(qtbot):
    editor = make_editor(qtbot)
    branch = editor.add_snippet("flow_if_else")
    branch.field("condition").setText("x > 0")
    editor.add_snippet("mouse_click", body=branch.bodies[0])
    typed = editor.add_snippet("key_type_text", body=branch.bodies[1])
    typed.field("text").setText("hi")

    code = block_ops.blocks_to_code(editor.blocks())
    assert code == (
        "if x > 0:\n"
        "    pyautogui.click()\n"
        "else:\n"
        "    pyautogui.typewrite('hi')"
    )


def test_function_definition_and_call(qtbot):
    editor = make_editor(qtbot)
    function = editor.add_snippet("logic_func_def")
    function.field("name").setText("move_and_click")
    function.field("params").setText("x, y")
    function.field("result").setText("x + y")

    child = editor.add_snippet("mouse_click", body=function.bodies[0])
    assert child in function.bodies[0]._widgets

    call = editor.add_snippet("logic_func_call")
    call.field("name").setText("move_and_click")
    call.field("args").setText("1, 2")
    call.field("variable").setText("result")

    code = block_ops.blocks_to_code(editor.blocks())
    assert "def move_and_click(x, y):" in code
    assert "    pyautogui.click()" in code
    assert "    return x + y" in code
    assert "result = move_and_click(1, 2)" in code


def test_return_block(qtbot):
    editor = make_editor(qtbot)
    ret = editor.add_snippet("logic_return")
    ret.field("value").setText("42")

    assert block_ops.blocks_to_code(editor.blocks()) == "return 42"


def test_delete_block(qtbot):
    editor = make_editor(qtbot)
    widget = editor.add_snippet("mouse_click")

    editor.delete_block(widget)

    assert editor.blocks() == []


def test_load_blocks_roundtrip(qtbot):
    editor = make_editor(qtbot)
    source = [
        Block("mouse_click"),
        Block(
            "flow_if_else",
            params={"condition": "x > 0"},
            children=[Block("mouse_double_click")],
            else_children=[Block("key_type_text", params={"text": "a"})],
        ),
    ]

    editor.load_blocks(source)

    loaded = editor.blocks()
    assert loaded[0].kind == "mouse_click"
    assert loaded[1].children[0].kind == "mouse_double_click"
    assert loaded[1].else_children[0].kind == "key_type_text"
    assert "else:" in block_ops.blocks_to_code(loaded)
