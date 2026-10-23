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


def test_python_code_category_has_line_and_multiline_items(qtbot):
    tree = StatementTree()
    qtbot.addWidget(tree)

    python_category = next(
        item
        for item, _children in tree._category_items
        if item.text(0) == "Python代码"
    )
    labels = [python_category.child(i).text(0) for i in range(python_category.childCount())]
    assert labels == ["Python代码行", "Python代码"]
    assert python_category.child(0).data(0, Qt.ItemDataRole.UserRole) == "empty"
    assert python_category.child(1).data(0, Qt.ItemDataRole.UserRole) == "python"


def test_statement_tree_toggle_all_categories(qtbot):
    tree = StatementTree()
    qtbot.addWidget(tree)

    assert tree.all_expanded()
    assert tree.toggle_all_expanded() is False
    assert not tree.all_expanded()
    assert tree.toggle_all_expanded() is True
    assert tree.all_expanded()


def test_drag_preview_is_a_small_block(qtbot):
    tree = StatementTree()
    qtbot.addWidget(tree)
    pixmap = tree._drag_pixmap("单击鼠标左键", "#3b82f6")
    assert not pixmap.isNull()
    assert pixmap.width() > 40
    assert pixmap.height() >= 24
