"""画布式积木：定位、参数输入、容器、判断块。"""

from PySide6.QtCore import QPoint

from hotkey.core import blocks as block_ops
from hotkey.core.models import Block
from hotkey.ui.widgets.block_canvas import BlockCanvasView, BlockWidget


def make_view(qtbot):
    view = BlockCanvasView()
    qtbot.addWidget(view)
    view.resize(900, 600)
    view.show()
    return view


def test_add_snippet_at_position(qtbot):
    view = make_view(qtbot)
    widget = view.add_snippet("mouse_move_to", QPoint(120, 80))

    assert isinstance(widget, BlockWidget)
    widget.field("x").setText("800")
    widget.field("y").setText("600")

    blocks = view.blocks()
    assert blocks[0].x == 120
    assert blocks[0].y == 80
    assert block_ops.blocks_to_code(blocks) == "pyautogui.moveTo(800, 600)"


def test_empty_block_has_code_field(qtbot):
    view = make_view(qtbot)
    widget = view.add_snippet("empty", QPoint(40, 40))

    widget.code_edit().setText("x = 1")

    assert block_ops.blocks_to_code(view.blocks()) == "x = 1"


def test_container_holds_children(qtbot):
    view = make_view(qtbot)
    loop = view.add_snippet("flow_for_3", QPoint(40, 40))
    view.add_snippet("mouse_click", body=loop.bodies[0])

    assert loop.height() > loop.header.height()
    code = block_ops.blocks_to_code(view.blocks())
    assert code == "for i in range(3):\n    pyautogui.click()"


def test_if_else_branches(qtbot):
    view = make_view(qtbot)
    branch = view.add_snippet("flow_if_else", QPoint(40, 40))
    branch.field("condition").setText("x > 0")

    view.add_snippet("mouse_click", body=branch.bodies[0])
    type_block = view.add_snippet("key_type_text", body=branch.bodies[1])
    type_block.field("text").setText("hi")

    code = block_ops.blocks_to_code(view.blocks())
    assert code == (
        "if x > 0:\n"
        "    pyautogui.click()\n"
        "else:\n"
        "    pyautogui.typewrite('hi')"
    )


def test_if_without_else_has_no_else_clause(qtbot):
    view = make_view(qtbot)
    branch = view.add_snippet("flow_if_else", QPoint(40, 40))
    branch.field("condition").setText("ok")
    view.add_snippet("mouse_click", body=branch.bodies[0])

    code = block_ops.blocks_to_code(view.blocks())
    assert "else:" not in code
    assert code.startswith("if ok:")


def test_delete_block(qtbot):
    view = make_view(qtbot)
    widget = view.add_snippet("mouse_click", QPoint(40, 40))

    view.canvas.delete_block(widget)

    assert view.blocks() == []


def test_load_preserves_positions(qtbot):
    view = make_view(qtbot)
    view.load_blocks(
        [
            Block("mouse_click", x=220, y=140),
            Block("key_type_text", params={"text": "a"}, x=60, y=320),
        ]
    )

    blocks = view.blocks()
    assert [block.kind for block in blocks] == ["mouse_click", "key_type_text"]
    assert blocks[0].x == 220
    assert blocks[0].y == 140
    assert blocks[1].x == 60
    assert blocks[1].y == 320


def test_nested_blocks_roundtrip(qtbot):
    view = make_view(qtbot)
    view.load_blocks(
        [
            Block(
                "flow_if_else",
                params={"condition": "x > 0"},
                children=[Block("mouse_click")],
                else_children=[Block("mouse_double_click")],
            )
        ]
    )

    loaded = view.blocks()[0]
    assert loaded.children[0].kind == "mouse_click"
    assert loaded.else_children[0].kind == "mouse_double_click"
    assert "else:" in block_ops.blocks_to_code([loaded])
