"""右侧积木栏：常驻输入框、拖入、嵌套、删除。"""

from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QDropEvent

from hotkey.core import blocks as block_ops
from hotkey.core.models import Block
from hotkey.ui.widgets.block_tree import BlockRow, BlockTree
from hotkey.ui.widgets.statement_tree import SNIPPET_MIME


def make_tree(qtbot):
    tree = BlockTree()
    qtbot.addWidget(tree)
    tree.show()
    tree.resize(640, 320)
    return tree


def row_of(tree, item):
    row = tree.itemWidget(item, 0)
    assert isinstance(row, BlockRow)
    return row


def test_append_fixed_snippet(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("mouse_click")
    row = row_of(tree, item)

    assert tree.topLevelItemCount() == 1
    assert row.values() == {}
    assert tree.blocks()[0].kind == "mouse_click"


def test_parameters_are_always_visible_fields(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("mouse_move_to")
    row = row_of(tree, item)

    x_field = row.field("x")
    y_field = row.field("y")
    assert x_field is not None and x_field.isVisibleTo(tree)
    assert y_field is not None
    assert x_field.placeholderText() == "x"

    x_field.setText("100")
    y_field.setText("200")

    assert tree.blocks()[0].params == {"x": "100", "y": "200"}
    assert block_ops.blocks_to_code(tree.blocks()) == "pyautogui.moveTo(100, 200)"


def test_text_field_is_quoted(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("dialog_alert")
    row = row_of(tree, item)

    row.field("text").setText("你好")

    assert block_ops.blocks_to_code(tree.blocks()) == "pyautogui.alert('你好')"


def test_block_snippet_accepts_children(qtbot):
    tree = make_tree(qtbot)
    loop = tree.append_snippet("flow_for_3")
    tree.append_snippet("mouse_click", parent=loop)

    assert loop.childCount() == 1
    loaded = tree.blocks()
    assert loaded[0].children[0].kind == "mouse_click"
    assert block_ops.blocks_to_code(loaded) == "for i in range(3):\n    pyautogui.click()"


def test_empty_block_has_code_field(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("empty")
    row = row_of(tree, item)
    edit = row.code_edit()

    assert edit is not None
    assert edit.text() == ""
    edit.setText("x = 1")

    assert tree.blocks()[0].text == "x = 1"
    assert block_ops.blocks_to_code(tree.blocks()) == "x = 1"


def test_delete_button_removes_row(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("mouse_click")
    row = row_of(tree, item)

    from PySide6.QtWidgets import QToolButton

    button = row.findChild(QToolButton)
    assert button is not None
    button.click()

    assert tree.topLevelItemCount() == 0


def test_load_blocks_preserves_params(qtbot):
    tree = make_tree(qtbot)
    tree.load_blocks(
        [
            Block(
                "mouse_move_to",
                text="移动鼠标到（10, 20）",
                params={"x": "10", "y": "20"},
            ),
            Block("flow_for_3", children=[Block("empty", text="x = 1")]),
        ]
    )

    assert tree.topLevelItemCount() == 2
    loaded = tree.blocks()
    assert loaded[0].params == {"x": "10", "y": "20"}
    assert loaded[1].children[0].text == "x = 1"

    row = row_of(tree, tree.topLevelItem(0))
    assert row.field("x").text() == "10"


def test_drop_from_palette_mime(qtbot):
    tree = make_tree(qtbot)

    mime = QMimeData()
    mime.setData(SNIPPET_MIME, b"mouse_click")
    event = QDropEvent(
        QPointF(4, 4),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    tree.dropEvent(event)

    assert tree.topLevelItemCount() == 1
    assert tree.blocks()[0].kind == "mouse_click"
    assert event.isAccepted()
