"""core/keymap 的单元测试。"""

import keyboard
import pytest

from hotkey.core import keymap


@pytest.mark.parametrize(
    ("qt", "expected"),
    [
        ("Ctrl+Shift+A", "ctrl+shift+a"),
        ("Ctrl+C", "ctrl+c"),
        ("Alt+F4", "alt+f4"),
        ("Meta+R", "win+r"),
        ("Ctrl++", "ctrl+plus"),
        ("Ctrl+Shift++", "ctrl+shift+plus"),
        ("PgUp", "page up"),
        ("PgDown", "page down"),
        ("Del", "delete"),
        ("Ins", "insert"),
        ("Esc", "esc"),
        ("Return", "enter"),
        ("Space", "space"),
        ("Up", "up"),
        ("CapsLock", "caps lock"),
        ("Print", "print screen"),
        ("F12", "f12"),
        ("Ctrl+,", "ctrl+comma"),
        ("Ctrl+1", "ctrl+1"),
    ],
)
def test_qt_to_keyboard(qt, expected):
    assert keymap.qt_to_keyboard(qt) == expected


def test_qt_to_keyboard_rejects_unknown():
    assert keymap.qt_to_keyboard("Ctrl+NotAKey") is None
    assert keymap.qt_to_keyboard("Hyper+A") is None
    assert keymap.qt_to_keyboard("") is None


def test_converted_names_are_accepted_by_keyboard():
    sequences = [
        "Ctrl+Shift+A",
        "Meta+R",
        "Ctrl++",
        "PgUp",
        "PgDown",
        "Del",
        "Ins",
        "CapsLock",
        "Print",
        "Ctrl+,",
        "Alt+F4",
    ]
    for sequence in sequences:
        converted = keymap.qt_to_keyboard(sequence)
        assert converted is not None, sequence
        keyboard.parse_hotkey(converted)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Shift+CTRL+a", "ctrl+shift+a"),
        ("ctrl+ctrl+a", "ctrl+a"),
        ("Meta+R", "win+r"),
        ("  Ctrl + Alt + Delete ", "ctrl+alt+delete"),
        ("windows+e", "win+e"),
        ("", ""),
    ],
)
def test_normalize_key(raw, expected):
    assert keymap.normalize_key(raw) == expected


def test_keyboard_to_qt():
    assert keymap.keyboard_to_qt("ctrl+shift+a") == "Ctrl+Shift+A"
    assert keymap.keyboard_to_qt("win+r") == "Meta+R"
    assert keymap.keyboard_to_qt("page up") == "PgUp"


def test_is_modifier_only():
    assert keymap.is_modifier_only("ctrl+shift")
    assert not keymap.is_modifier_only("ctrl+a")
