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


def test_one_file_can_contain_multiple_hotkeys(tmp_path):
    storage.save(
        tmp_path / "group.hk",
        [
            HotKey(key="ctrl+1", description="第一个", id="one"),
            HotKey(key="ctrl+2", description="第二个", id="two"),
        ],
    )

    scripts = ScriptLibrary(tmp_path).load()

    assert len(scripts) == 2
    assert [script.name for script in scripts] == ["第一个", "第二个"]
    assert scripts[0].path == scripts[1].path == tmp_path / "group.hk"


def test_saving_one_hotkey_preserves_siblings(tmp_path):
    storage.save(
        tmp_path / "group.hk",
        [HotKey(key="ctrl+1", id="one"), HotKey(key="ctrl+2", id="two")],
    )
    library = ScriptLibrary(tmp_path)
    scripts = library.load()

    scripts[0].blocks = [Block("mouse_click")]
    library.save(scripts[0])

    loaded = library.load()
    assert len(loaded) == 2
    assert loaded[0].id == "one"
    assert loaded[0].blocks[0].kind == "mouse_click"
    assert loaded[1].id == "two"


def test_deleting_one_hotkey_keeps_file_until_last(tmp_path):
    storage.save(
        tmp_path / "group.hk",
        [HotKey(key="ctrl+1", id="one"), HotKey(key="ctrl+2", id="two")],
    )
    library = ScriptLibrary(tmp_path)
    scripts = library.load()
    path = scripts[0].path

    library.delete(scripts[0])
    assert path.exists()
    assert [script.id for script in library.load()] == ["two"]

    library.delete(scripts[1])
    assert not path.exists()


def test_import_copy_keeps_all_hotkeys(tmp_path):
    source = tmp_path / "外部队列.hk"
    storage.save(
        source,
        [HotKey(key="f1", id="one"), HotKey(key="f2", id="two")],
    )
    library = ScriptLibrary(tmp_path)

    imported = library.import_copy(source)

    assert len(imported) == 2
    assert imported[0].path == imported[1].path
    assert imported[0].path.name.startswith("外部队列")
    assert len([script for script in library.load() if script.path == imported[0].path]) == 2
