"""core/storage 的单元测试：迁移、去重、原子写。"""

import json

import pytest

from hotkey.core import storage
from hotkey.core.models import HotKey


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_default_path_honours_hotkey_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOTKEY_HOME", str(tmp_path))
    path = storage.default_config_path()
    assert path == tmp_path / "hotkeys.json"
    assert path.parent.is_dir()


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


def test_v3_text_blocks_are_migrated_to_params(tmp_path):
    path = write_json(
        tmp_path / "hotkeys.json",
        {
            "version": 3,
            "hotkeys": [
                {
                    "id": "old",
                    "key": "f1",
                    "description": "旧积木",
                    "script": "",
                    "blocks": [
                        {
                            "kind": "mouse_move_to",
                            "text": "移动鼠标到（10, 20）",
                            "children": [],
                        }
                    ],
                }
            ],
        },
    )

    hotkeys, warnings = storage.load_document(path)
    block = hotkeys[0].blocks[0]

    assert block.params == {"x": "10", "y": "20"}
    assert hotkeys[0].script == "pyautogui.moveTo(10, 20)"
    assert any("迁移" in warning for warning in warnings)


def test_v4_params_roundtrip(tmp_path):
    from hotkey.core.models import Block

    path = tmp_path / "hotkeys.json"
    hotkey = HotKey(
        key="f1",
        id="fixed",
        blocks=[
            Block(
                "dialog_alert",
                text="弹出提示：你好",
                params={"text": "你好"},
            )
        ],
    )

    storage.save(path, [hotkey])
    loaded, _ = storage.load_document(path)

    assert loaded[0].blocks[0].params == {"text": "你好"}
    assert loaded[0].blocks[0].text == "弹出提示：你好"
    assert loaded[0].script == "pyautogui.alert('你好')"


def test_save_derives_script_from_blocks(tmp_path):
    from hotkey.core.models import Block

    path = tmp_path / "hotkeys.json"
    hotkey = HotKey(
        key="f1",
        script="stale",
        blocks=[Block("mouse_click")],
    )

    storage.save(path, [hotkey])
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["hotkeys"][0]["script"] == "pyautogui.click()"


def test_positions_and_else_branch_roundtrip(tmp_path):
    from hotkey.core.models import Block

    path = tmp_path / "hotkeys.json"
    hotkey = HotKey(
        key="f1",
        id="fixed",
        blocks=[
            Block(
                "flow_if_else",
                params={"condition": "x > 0"},
                children=[Block("mouse_click")],
                else_children=[Block("mouse_double_click")],
                x=120,
                y=80,
            )
        ],
    )

    storage.save(path, [hotkey])
    loaded, _ = storage.load_document(path)
    block = loaded[0].blocks[0]

    assert block.x == 120
    assert block.y == 80
    assert block.children[0].kind == "mouse_click"
    assert block.else_children[0].kind == "mouse_double_click"
    assert loaded[0].script == (
        "if x > 0:\n"
        "    pyautogui.click()\n"
        "else:\n"
        "    pyautogui.doubleClick()"
    )
