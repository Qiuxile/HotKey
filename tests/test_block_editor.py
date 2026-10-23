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


def set_value_slot(widget, name, text, mode="code"):
    slot = widget.value_slot(name)
    assert slot is not None
    slot.mode_combo.setCurrentIndex(slot.mode_combo.findData(mode))
    slot.edit.setText(text)
    return slot


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


def test_reorder_by_drag_target(qtbot):
    editor = make_editor(qtbot)
    first = editor.add_snippet("mouse_click")
    second = editor.add_snippet("mouse_double_click")
    third = editor.add_snippet("mouse_right_click")

    editor.reorder_block(third, first, after=False)
    assert [block.kind for block in editor.blocks()] == [
        "mouse_right_click",
        "mouse_click",
        "mouse_double_click",
    ]

    editor.reorder_block(first, third, after=True)
    assert [block.kind for block in editor.blocks()] == [
        "mouse_right_click",
        "mouse_click",
        "mouse_double_click",
    ]
    assert all(widget.drag_handle is not None for widget in editor._blocks)


def test_container_holds_children(qtbot):
    editor = make_editor(qtbot)
    loop = editor.add_snippet("flow_for_range")
    loop.field("name").setText("i")
    loop.field("start").setText("0")
    loop.field("end").setText("3")
    loop.field("step").setText("1")
    editor.add_snippet("mouse_click", body=loop.bodies[0])

    assert loop.height() > loop.header.height()
    assert block_ops.blocks_to_code(editor.blocks()) == (
        "for i in range(0, 3, 1):\n    pyautogui.click()"
    )


def test_if_else_branches(qtbot):
    editor = make_editor(qtbot)
    branch = editor.add_snippet("flow_if_else")
    set_value_slot(branch, "condition", "x > 0")
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

    ret = editor.add_snippet("flow_return", body=function.bodies[0])
    set_value_slot(ret, "value", "x + y")

    call = editor.add_snippet("logic_func_plain")
    call.field("name").setText("move_and_click")
    call.field("args").setText("1, 2")

    assign = editor.add_snippet("logic_set")
    assign.field("name").setText("result")
    slot = assign.value_slot("value")
    assert slot is not None
    slot.set_expression(
        Block(
            kind="value_func_call",
            params={"name": "move_and_click", "args": "1, 2"},
        )
    )

    code = block_ops.blocks_to_code(editor.blocks())
    assert "def move_and_click(x, y):" in code
    assert "    return x + y" in code
    assert "move_and_click(1, 2)" in code
    assert "result = move_and_click(1, 2)" in code


def test_return_block(qtbot):
    editor = make_editor(qtbot)
    ret = editor.add_snippet("flow_return")
    set_value_slot(ret, "value", "42")

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
            value_modes={"condition": "code"},
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
