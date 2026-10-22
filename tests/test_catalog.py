"""积木目录：中文模板、参数解析、代码生成。"""

import pytest

from hotkey.core import blocks, catalog
from hotkey.core.models import Block


def test_catalog_shape():
    assert len(catalog.SNIPPETS) == 36
    assert len(catalog.CATEGORIES) == 5
    ids = [snippet.id for snippet in catalog.SNIPPETS]
    assert len(ids) == len(set(ids))


def test_every_snippet_belongs_to_known_category():
    known = {category for category, _ in catalog.CATEGORIES}
    assert all(snippet.category in known for snippet in catalog.SNIPPETS)


def test_blank_text_leaves_parameters_empty():
    snippet = catalog.snippet("mouse_move_to")
    assert snippet.blank_text() == "移动鼠标到（, ）"
    assert snippet.parse(snippet.blank_text()) == {"x": "", "y": ""}


def test_parameter_parsing_and_code_generation():
    snippet = catalog.snippet("mouse_move_to")
    text = "移动鼠标到（800, 600）"

    assert snippet.parse(text) == {"x": "800", "y": "600"}
    assert snippet.code_for_text(text) == "pyautogui.moveTo(800, 600)"


def test_quoted_parameters_are_escaped():
    snippet = catalog.snippet("dialog_alert")
    code = snippet.code_for_text("弹出提示：他说'你好'")
    assert code == "pyautogui.alert(\"他说'你好'\")"


def test_fixed_snippet_only_accepts_its_own_label():
    snippet = catalog.snippet("mouse_click")
    assert snippet.parse("单击鼠标左键") == {}
    assert snippet.parse("改成别的") is None
    assert snippet.code_for_text("单击鼠标左键") == "pyautogui.click()"


def test_unknown_parameter_text_is_rejected():
    snippet = catalog.snippet("mouse_move_to")
    assert snippet.parse("移动鼠标到 800, 600") is None


def test_block_snippets():
    for_id = "flow_for_3"
    assert catalog.is_container(for_id)
    assert not catalog.is_container("mouse_click")
    assert not catalog.is_container("empty")


def test_blocks_to_code_nests_children():
    tree = [
        catalog.snippet("mouse_click"),
    ]
    assert tree[0].code_for_text(tree[0].blank_text()) == "pyautogui.click()"

    code = blocks.blocks_to_code(
        [
            Block("flow_for_3", "重复执行 3 次", [
                Block("mouse_click", "单击鼠标左键"),
            ]),
            Block("empty", "x = 1"),
        ]
    )
    assert "for i in range(3):" in code
    assert "    pyautogui.click()" in code
    assert code.endswith("x = 1")


def test_empty_block_without_code_is_ignored():
    assert blocks.blocks_to_code([Block("empty", "空")]) == ""
    assert blocks.blocks_to_code([Block("empty", "")]) == ""


@pytest.mark.parametrize("snippet", catalog.SNIPPETS, ids=lambda s: s.id)
def test_templates_are_consistent(snippet):
    text = snippet.blank_text()
    assert snippet.parse(text) is not None
    if not snippet.fields():
        assert snippet.code_for_text(text)
