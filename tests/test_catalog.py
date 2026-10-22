"""core/catalog 的单元测试：数量、模板可编译性、块语句光标位置。"""

from hotkey.core import catalog


def test_catalog_shape():
    assert len(catalog.SNIPPETS) == 36
    assert len(catalog.CATEGORIES) == 5
    ids = [snippet.id for snippet in catalog.SNIPPETS]
    assert len(ids) == len(set(ids))


def test_every_snippet_belongs_to_known_category():
    known = {category for category, _ in catalog.CATEGORIES}
    assert all(snippet.category in known for snippet in catalog.SNIPPETS)


def test_non_block_templates_compile():
    for snippet in catalog.SNIPPETS:
        if snippet.block:
            continue
        text, _ = snippet.render()
        compile(text, f"<{snippet.id}>", "exec")


def test_block_snippets_render_indent_and_cursor():
    for snippet in catalog.SNIPPETS:
        if not snippet.block:
            continue
        text, offset = snippet.render()
        assert text.rstrip().endswith(":")
        assert text.endswith(catalog.INDENT)
        assert offset == len(text)
        assert "${" not in text


def test_grouped_by_category_covers_everything():
    grouped = catalog.snippets_by_category()
    counted = sum(len(items) for items in grouped.values())
    assert counted == len(catalog.SNIPPETS)
    assert list(grouped) == [category for category, _ in catalog.CATEGORIES]


def test_lookup_helpers():
    assert catalog.snippet("flow_for_3").block is True
    assert catalog.category_label("flow") == "⏱️ 流程控制"
