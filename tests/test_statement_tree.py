"""积木柜：预览文案与搜索过滤。"""

from PySide6.QtCore import Qt

from hotkey.core import catalog
from hotkey.ui.widgets.statement_tree import StatementTree


def test_snippet_preview_uses_placeholders():
    snippet = catalog.snippet("mouse_move_to")
    preview = snippet.preview()
    assert "x" in preview
    assert "y" in preview
    assert "（, ）" not in preview


def test_statement_tree_filters_by_chinese_and_code(qtbot):
    tree = StatementTree()
    qtbot.addWidget(tree)
    tree.show()

    tree.set_filter("鼠标")
    assert any(not child.isHidden() for _, children in tree._category_items for child in children)

    tree.set_filter("locateOnScreen")
    visible = [
        child
        for _, children in tree._category_items
        for child in children
        if not child.isHidden()
    ]
    assert visible
    assert all(
        "locateOnScreen" in child.toolTip(0) for child in visible
    )

    tree.set_filter("不存在积木")
    assert not any(
        not child.isHidden()
        for _, children in tree._category_items
        for child in children
    )
    assert tree._no_result_item is not None
    assert not tree._no_result_item.isHidden()

    tree.set_filter("")
    assert tree._no_result_item is not None
    assert tree._no_result_item.isHidden()


def test_statement_tree_empty_item_can_be_searched(qtbot):
    tree = StatementTree()
    qtbot.addWidget(tree)

    tree.set_filter("空")
    assert tree._empty_item is not None
    assert not tree._empty_item.isHidden()
    assert tree._empty_item.data(0, Qt.ItemDataRole.UserRole) == "empty"


def test_statement_tree_toggle_all_categories(qtbot):
    tree = StatementTree()
    qtbot.addWidget(tree)

    assert tree.all_expanded()
    assert tree.toggle_all_expanded() is False
    assert not tree.all_expanded()
    assert tree.toggle_all_expanded() is True
    assert tree.all_expanded()
