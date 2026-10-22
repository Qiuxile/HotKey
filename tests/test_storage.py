"""core/storage 的单元测试：迁移、去重、原子写。"""

import json

import pytest

from hotkey.core import storage
from hotkey.core.models import HotKey


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_default_path_is_under_appdata():
    path = storage.default_config_path()
    assert path.name == "hotkeys.json"
    assert "HotKey" in path.parts


def test_load_missing_file_returns_empty(tmp_path):
    assert storage.load(tmp_path / "missing.json") == []


def test_v1_list_is_migrated(tmp_path):
    path = write_json(
        tmp_path / "hotkeys.json",
        [
            {
                "key": "F1",
                "description": "旧配置",
                "code": ["x = 1", "print(x)"],
            }
        ],
    )

    hotkeys, warnings = storage.load_document(path)

    assert len(hotkeys) == 1
    assert hotkeys[0].key == "f1"
    assert hotkeys[0].script == "x = 1\nprint(x)"
    assert hotkeys[0].enabled is True
    assert hotkeys[0].id
    assert any("迁移" in warning for warning in warnings)


def test_v2_roundtrip(tmp_path):
    hotkey = HotKey(
        key="ctrl+shift+a",
        description="弹出提示",
        script="pyautogui.alert('hi')",
        id="fixed-id",
    )
    path = tmp_path / "nested" / "hotkeys.json"

    storage.save(path, [hotkey])
    loaded, warnings = storage.load_document(path)

    assert warnings == []
    assert len(loaded) == 1
    assert loaded[0].to_dict() == hotkey.to_dict()


def test_duplicate_keys_are_disabled(tmp_path):
    path = write_json(
        tmp_path / "hotkeys.json",
        [
            {"key": "Ctrl+A", "script": "x = 1"},
            {"key": "ctrl+a", "script": "x = 2"},
        ],
    )

    hotkeys, warnings = storage.load_document(path)

    assert len(hotkeys) == 2
    assert hotkeys[0].enabled is True
    assert hotkeys[1].enabled is False
    assert any("重复" in warning for warning in warnings)


def test_invalid_entries_are_skipped(tmp_path):
    path = write_json(
        tmp_path / "hotkeys.json",
        [
            "not-an-object",
            {"description": "缺少 key"},
            {"key": "   "},
            {"key": "F2", "description": 123},
        ],
    )

    hotkeys, warnings = storage.load_document(path)

    assert len(hotkeys) == 1
    assert hotkeys[0].description == "123"
    skipped = [warning for warning in warnings if "跳过" in warning]
    assert len(skipped) == 3


def test_corrupt_json_raises(tmp_path):
    path = tmp_path / "hotkeys.json"
    path.write_text("{not json", encoding="utf-8")

    with pytest.raises(storage.StorageError):
        storage.load_document(path)


def test_save_keeps_backup_and_removes_tmp(tmp_path):
    path = tmp_path / "hotkeys.json"
    storage.save(path, [HotKey(key="f1")])
    storage.save(path, [HotKey(key="f2")])

    assert path.exists()
    assert path.with_name(path.name + ".bak").exists()
    assert not path.with_name(path.name + ".tmp").exists()
