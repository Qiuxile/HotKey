"""热键列表模型（脚本库视图）与搜索代理。"""

from PySide6.QtCore import Qt

from hotkey.core.models import HotKey
from hotkey.ui.hotkey_model import HotKeyFilterProxy, HotKeyTableModel


def make_entries():
    return [
        HotKey(key="ctrl+a", name="alpha", description="第一个", id="id-a"),
        HotKey(key="ctrl+b", name="beta", description="第二个", id="id-b"),
        HotKey(key="", name="gamma", description="无热键", id="id-c"),
    ]


def test_model_displays_name_hotkey_status():
    model = HotKeyTableModel(make_entries())

    assert model.rowCount() == 3
    assert model.columnCount() == 3
    assert model.data(model.index(0, 0)) == "alpha"
    assert model.data(model.index(0, 1)) == "Ctrl+A"
    assert model.data(model.index(2, 1)) == "—"
    assert model.data(model.index(2, 2)) == "启用"
    assert model.data(model.index(0, 0), Qt.ItemDataRole.UserRole) == "id-a"


def test_model_toggle_add_remove():
    model = HotKeyTableModel(make_entries())

    model.toggle(0)
    assert model.entry(0).enabled is False
    assert model.data(model.index(0, 2)) == "停用"

    new_entry = HotKey(key="ctrl+9", name="new")
    row = model.add(new_entry)
    assert row == 3
    assert model.row_of(new_entry.id) == 3

    model.remove(1)
    assert model.rowCount() == 3
    assert model.row_of("id-b") is None


def test_proxy_search_maps_to_source_row(qtbot):
    model = HotKeyTableModel(make_entries())
    proxy = HotKeyFilterProxy()
    proxy.setSourceModel(model)

    proxy.set_search_text("beta")
    assert proxy.rowCount() == 1

    proxy_index = proxy.index(0, 0)
    source_index = proxy.mapToSource(proxy_index)
    assert model.entry(source_index.row()).id == "id-b"

    proxy.set_search_text("")
    assert proxy.rowCount() == 3


def test_proxy_searches_name_key_and_description(qtbot):
    model = HotKeyTableModel(make_entries())
    proxy = HotKeyFilterProxy()
    proxy.setSourceModel(model)

    proxy.set_search_text("ctrl")
    assert proxy.rowCount() == 2

    proxy.set_search_text("GAMMA")
    assert proxy.rowCount() == 1

    proxy.set_search_text("第二个")
    assert proxy.rowCount() == 1
