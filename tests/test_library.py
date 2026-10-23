"""热键文件流：清单导入、保存、移除、删除。"""

from hotkey.core import storage
from hotkey.core.library import ScriptLibrary, _migrate_script_dir
from hotkey.core.models import Block, HotKey


def test_new_library_starts_empty_even_if_folder_has_files(tmp_path):
    storage.save(tmp_path / "loose.hk", [HotKey(key="f1", id="loose")])

    library = ScriptLibrary(tmp_path)

    assert library.load() == []


def test_register_and_save_add_files_to_manifest(tmp_path):
    storage.save(tmp_path / "existing.hk", [HotKey(key="f1", id="existing")])
    library = ScriptLibrary(tmp_path)
    library.register(tmp_path / "existing.hk")

    script = HotKey(key="", name="demo", blocks=[Block("mouse_click")])
    path = library.save(script)

    loaded = library.load()
    assert {item.id for item in loaded} == {"existing", script.id}
    assert path.exists()
    assert path.name.endswith(".hk")


def test_duplicate_keys_are_disabled(tmp_path):
    library = ScriptLibrary(tmp_path)
    library.save(HotKey(key="ctrl+a", id="a", name="a"))
    library.save(HotKey(key="ctrl+a", id="b", name="b"))

    scripts = library.load()

    assert scripts[0].enabled is True
    assert scripts[1].enabled is False
    assert any("重复" in warning for warning in library.warnings)


def test_legacy_hotkeys_file_is_split_only_when_migrated(tmp_path):
    storage.save(
        tmp_path / "hotkeys.json",
        [HotKey(key="f1", description="脚本一", id="old")],
    )

    library = ScriptLibrary(tmp_path)
    library._migrate_legacy()
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
    assert script.name == "demo"
    assert library.load()[0].path == path

    library.delete(script)
    assert not path.exists()
    assert library.load() == []


def test_remove_keeps_file_but_removes_from_manifest(tmp_path):
    library = ScriptLibrary(tmp_path)
    script = HotKey(key="", name="keep", blocks=[Block("mouse_click")])
    path = library.save(script)

    library.remove(script)

    assert path.exists()
    assert library.load() == []

    library.register(path)
    assert library.load()[0].path == path


def test_legacy_jsons_folder_is_renamed_to_hks(tmp_path):
    old = tmp_path / "jsons"
    old.mkdir()
    (old / "demo.hk").write_text("{}", encoding="utf-8")

    _migrate_script_dir(tmp_path)

    assert not old.exists()
    assert (tmp_path / "hks" / "demo.hk").exists()
