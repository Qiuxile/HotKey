"""积木目录：JSON 加载、中文分段、参数与代码生成。"""

import pytest

from hotkey.core import blocks, catalog
from hotkey.core.models import Block


def test_catalog_shape():
    assert len(catalog.SNIPPETS) == 37
    assert len(catalog.CATEGORIES) == 5
    ids = [snippet.id for snippet in catalog.SNIPPETS]
    assert len(ids) == len(set(ids))


def test_container_slots_and_hidden_blocks():
    assert catalog.snippet("flow_for_3").slots == ("重复内容",)
    assert catalog.snippet("flow_if").hidden is True

    if_else = catalog.snippet("flow_if_else")
    assert if_else.slots == ("那么", "否则")
    assert if_else.params[0].kind == "code"
    assert if_else.code_for_values({"condition": "x > 0"}) == "if x > 0:"


def test_categories_have_colors():
    for category in catalog.CATEGORIES:
        assert category.color.startswith("#")
        assert category.accent.startswith("#")
    assert catalog.category("mouse").label == "🖱️ 鼠标操作"


def test_segments_split_label_and_params():
    segments = catalog.snippet("mouse_move_to").segments()

    assert segments[0] == "移动鼠标到（"
    assert isinstance(segments[1], catalog.Param)
    assert segments[1].name == "x"
    assert segments[2] == ", "
    assert segments[3].name == "y"
    assert segments[4] == "）"


def test_blank_values_and_render():
    snippet = catalog.snippet("mouse_move_to")

    assert snippet.blank_values() == {"x": "", "y": ""}
    assert snippet.render({}) == "移动鼠标到（, ）"
    assert snippet.render({"x": "800", "y": "600"}) == "移动鼠标到（800, 600）"


def test_number_params_generate_code():
    snippet = catalog.snippet("mouse_move_to")
    code = snippet.code_for_values({"x": "800", "y": "600"})

    assert code == "pyautogui.moveTo(800, 600)"


def test_text_params_are_quoted_and_escaped():
    snippet = catalog.snippet("dialog_alert")
    code = snippet.code_for_values({"text": "他说'你好'"})

    assert code == "pyautogui.alert(\"他说'你好'\")"


def test_parse_text_recovers_params():
    snippet = catalog.snippet("mouse_move_to")

    assert snippet.parse_text("移动鼠标到（800, 600）") == {
        "x": "800",
        "y": "600",
    }
    assert snippet.parse_text("移动鼠标到（, ）") == {"x": "", "y": ""}
    assert snippet.parse_text("乱改一通") is None


def test_fixed_snippet_label_roundtrip():
    snippet = catalog.snippet("mouse_click")

    assert snippet.segments() == ["单击鼠标左键"]
    assert snippet.parse_text("单击鼠标左键") == {}
    assert snippet.parse_text("别的文字") is None
    assert snippet.code_for_values({}) == "pyautogui.click()"


def test_container_flags():
    assert catalog.is_container("flow_for_3")
    assert not catalog.is_container("mouse_click")
    assert not catalog.is_container("empty")


def test_nested_blocks_generate_indented_code():
    tree = [
        Block(
            "flow_for_3",
            children=[
                Block("mouse_move_to", params={"x": "10", "y": "20"}),
            ],
        )
    ]

    code = blocks.blocks_to_code(tree)

    assert code == "for i in range(3):\n    pyautogui.moveTo(10, 20)"


def test_empty_block_uses_raw_code():
    assert blocks.blocks_to_code([Block("empty", text="x = 1")]) == "x = 1"
    assert blocks.blocks_to_code([Block("empty", text="")]) == ""
    assert blocks.blocks_to_code([Block("empty", text="空")]) == ""


@pytest.mark.parametrize("snippet", catalog.SNIPPETS, ids=lambda s: s.id)
def test_every_snippet_renders_and_parses(snippet):
    text = snippet.render(snippet.blank_values())
    assert snippet.parse_text(text) is not None
    assert snippet.code_for_values(snippet.blank_values()) is not None
