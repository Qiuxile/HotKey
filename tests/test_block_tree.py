"""右侧积木栏：拖入、嵌套、编辑校验、删除。"""

from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QDropEvent

from hotkey.core import blocks as block_ops
from hotkey.core.models import Block
from hotkey.ui.widgets.block_tree import BlockTree, EMPTY_TEXT
from hotkey.ui.widgets.statement_tree import SNIPPET_MIME


def make_tree(qtbot):
    tree = BlockTree()
    qtbot.addWidget(tree)
    return tree


def test_append_fixed_snippet(qtbot):
    tree = make_tree(qtbot)
    tree.append_snippet("mouse_click")

    assert tree.topLevelItemCount() == 1
    assert tree.blocks() == [Block("mouse_click", "单击鼠标左键")]


def test_append_parameterized_snippet_leaves_blank(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("mouse_move_to")

    assert item.text(0) == "移动鼠标到（, ）"


def test_fill_parameter_in_place(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("mouse_move_to")

    item.setText(0, "移动鼠标到（100, 200）")

    assert tree.blocks()[0].text == "移动鼠标到（100, 200）"
    assert (
        block_ops.blocks_to_code(tree.blocks())
        == "pyautogui.moveTo(100, 200)"
    )


def test_invalid_edit_is_reverted(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("mouse_move_to")
    messages = []
    tree.message.connect(messages.append)

    item.setText(0, "乱改一通")

    assert item.text(0) == "移动鼠标到（, ）"
    assert messages


def test_block_snippet_accepts_children(qtbot):
    tree = make_tree(qtbot)
    loop = tree.append_snippet("flow_for_3")
    tree.append_snippet("mouse_click", parent=loop)

    assert loop.childCount() == 1
    tree_blocks = tree.blocks()
    assert tree_blocks[0].kind == "flow_for_3"
    assert tree_blocks[0].children[0].kind == "mouse_click"

    code = block_ops.blocks_to_code(tree_blocks)
    assert code == "for i in range(3):\n    pyautogui.click()"


def test_empty_block_starts_as_placeholder(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("empty")

    assert item.text(0) == EMPTY_TEXT
    assert tree.blocks()[0].text == ""

    item.setText(0, "x = 1")
    assert tree.blocks()[0].text == "x = 1"
    assert block_ops.blocks_to_code(tree.blocks()) == "x = 1"


def test_remove_item(qtbot):
    tree = make_tree(qtbot)
    item = tree.append_snippet("mouse_click")
    tree.setCurrentItem(item)

    tree._remove_item(item)

    assert tree.topLevelItemCount() == 0
    assert tree.blocks() == []


def test_load_blocks_roundtrip(qtbot):
    tree = make_tree(qtbot)
    source = [
        Block("mouse_click", "单击鼠标左键"),
        Block("flow_for_3", "重复执行 3 次", [Block("empty", "x = 1")]),
    ]

    tree.load_blocks(source)

    assert tree.topLevelItemCount() == 2
    loaded = tree.blocks()
    assert loaded[0].kind == "mouse_click"
    assert loaded[1].children[0].text == "x = 1"


def test_drop_from_palette_mime(qtbot):
    tree = make_tree(qtbot)
    tree.show()
    tree.resize(320, 200)

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
    assert tree.topLevelItem(0).text(0) == "单击鼠标左键"
    assert event.isAccepted()
