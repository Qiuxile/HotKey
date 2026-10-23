"""单文件脚本库：加载、迁移、保存、删除。"""

from hotkey.core import storage
from hotkey.core.library import ScriptLibrary
from hotkey.core.models import Block, HotKey


def test_loads_one_script_per_file(tmp_path):
    storage.save(
        tmp_path / "a.hk",
        [HotKey(key="ctrl+a", id="a", blocks=[Block("mouse_click")])],
    )
    storage.save(tmp_path / "b.hk", [HotKey(key="", id="b")])

    library = ScriptLibrary(tmp_path)
    scripts = library.load()

    assert [script.name for script in scripts] == ["a", "b"]
    assert scripts[0].path == tmp_path / "a.hk"
    assert scripts[0].key == "ctrl+a"
    assert scripts[1].key == ""


def test_json_scripts_are_renamed_to_hk(tmp_path):
    storage.save(tmp_path / "old.json", [HotKey(key="", id="old")])

    library = ScriptLibrary(tmp_path)
    scripts = library.load()

    assert not (tmp_path / "old.json").exists()
    assert (tmp_path / "old.hk").exists()
    assert scripts[0].path == tmp_path / "old.hk"
    assert any(".hk" in warning for warning in library.warnings)


def test_duplicate_keys_are_disabled(tmp_path):
    storage.save(tmp_path / "a.hk", [HotKey(key="ctrl+a", id="a")])
    storage.save(tmp_path / "b.hk", [HotKey(key="ctrl+a", id="b")])

    library = ScriptLibrary(tmp_path)
    scripts = library.load()

    assert scripts[0].enabled is True
    assert scripts[1].enabled is False
    assert any("重复" in warning for warning in library.warnings)


def test_legacy_hotkeys_file_is_split(tmp_path):
    storage.save(
        tmp_path / "hotkeys.json",
        [HotKey(key="f1", description="脚本一", id="old")],
    )

    library = ScriptLibrary(tmp_path)
    scripts = library.load()

    assert len(scripts) == 1
    assert scripts[0].key == "f1"
    assert scripts[0].path is not None
    assert scripts[0].path.name.endswith(".hk")
    assert not (tmp_path / "hotkeys.json").exists()
    assert (tmp_path / "hotkeys.json.migrated").exists()


def test_save_and_delete(tmp_path):
    library = ScriptLibrary(tmp_path)
    script = HotKey(key="", name="demo", blocks=[Block("mouse_click")])

    path = library.save(script)
    assert path.exists()
    assert path.name.endswith(".hk")
    assert script.name == "demo"

    loaded = library.load()
    assert loaded[0].name == "demo"
    assert loaded[0].path == path

    library.delete(script)
    assert not path.exists()
