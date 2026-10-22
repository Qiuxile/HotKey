"""热键名称转换：Qt 键序列 <-> keyboard 库键名（不依赖 Qt）。"""

from __future__ import annotations

from typing import Iterable

MODIFIER_ORDER = ("ctrl", "alt", "shift", "win")

_MODIFIER_ALIASES = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "meta": "win",
    "win": "win",
    "windows": "win",
    "super": "win",
}

_KEY_ALIASES = {
    "space": "space",
    "return": "enter",
    "enter": "enter",
    "tab": "tab",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "insert": "insert",
    "ins": "insert",
    "home": "home",
    "end": "end",
    "page up": "page up",
    "pageup": "page up",
    "pgup": "page up",
    "page down": "page down",
    "pagedown": "page down",
    "pgdown": "page down",
    "esc": "esc",
    "escape": "esc",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "caps lock": "caps lock",
    "capslock": "caps lock",
    "num lock": "num lock",
    "numlock": "num lock",
    "scroll lock": "scroll lock",
    "scrolllock": "scroll lock",
    "print screen": "print screen",
    "print": "print screen",
    "prtsc": "print screen",
    "sysrq": "print screen",
    "pause": "pause",
    "menu": "menu",
    "plus": "plus",
    "+": "plus",
    "minus": "minus",
    "-": "minus",
    "comma": "comma",
    ",": "comma",
    "period": "period",
    ".": "period",
    "slash": "slash",
    "/": "slash",
    "semicolon": "semicolon",
    ";": "semicolon",
    "quote": "quote",
    "apostrophe": "quote",
    "'": "quote",
    "left bracket": "left bracket",
    "[": "left bracket",
    "right bracket": "right bracket",
    "]": "right bracket",
    "backslash": "backslash",
    "\\": "backslash",
    "grave": "grave",
    "`": "grave",
    "equals": "equals",
    "=": "equals",
}

_KEYBOARD_TO_QT = {
    "ctrl": "Ctrl",
    "alt": "Alt",
    "shift": "Shift",
    "win": "Meta",
    "enter": "Return",
    "page up": "PgUp",
    "page down": "PgDown",
    "delete": "Del",
    "insert": "Ins",
    "esc": "Esc",
    "space": "Space",
    "tab": "Tab",
    "backspace": "Backspace",
    "up": "Up",
    "down": "Down",
    "left": "Left",
    "right": "Right",
    "plus": "+",
    "minus": "-",
    "comma": ",",
    "period": ".",
    "slash": "/",
    "semicolon": ";",
    "quote": "'",
    "left bracket": "[",
    "right bracket": "]",
    "backslash": "\\",
    "grave": "`",
    "equals": "=",
}


def _canonical_key(token: str) -> str | None:
    lower = token.strip().lower()
    if not lower:
        return None
    if lower in _KEY_ALIASES:
        return _KEY_ALIASES[lower]
    if len(lower) == 1 and (lower.isalnum() or lower in "=,./;'[]\\-`"):
        return lower
    if lower.startswith("f") and lower[1:].isdigit() and 1 <= int(lower[1:]) <= 24:
        return lower
    return None


def _split_sequence(sequence: str) -> tuple[list[str], str] | None:
    """把 "Ctrl+Shift+A" 拆成 (修饰键, 主键)，并处理 "+" 本身。"""
    text = sequence.strip()
    if not text:
        return None

    if text.endswith("++"):
        # QKeySequence 把加号键表示为 "Ctrl++"
        head, key_token = text[:-2], "+"
        raw_modifiers = [part for part in head.split("+") if part]
    else:
        parts = text.split("+")
        if len(parts) == 1:
            raw_modifiers, key_token = [], parts[0]
        else:
            raw_modifiers, key_token = parts[:-1], parts[-1]

    modifiers: list[str] = []
    for raw in raw_modifiers:
        alias = _MODIFIER_ALIASES.get(raw.strip().lower())
        if alias is None:
            return None
        if alias not in modifiers:
            modifiers.append(alias)

    return modifiers, key_token.strip()


def qt_to_keyboard(sequence: str) -> str | None:
    """把 Qt 的 "Ctrl+Shift+A" 转成 keyboard 库的 "ctrl+shift+a"。"""
    split = _split_sequence(sequence)
    if split is None:
        return None
    modifiers, key_token = split
    key = _canonical_key(key_token)
    if key is None:
        return None
    return "+".join(modifiers + [key])


def keyboard_to_qt(key: str) -> str:
    """把 keyboard 键名转回 Qt 显示形式。"""
    parts = [part for part in key.split("+") if part]
    mapped = [_KEYBOARD_TO_QT.get(part, part.upper()) for part in parts]
    return "+".join(mapped)


def normalize_key(key: str) -> str:
    """规范化热键字符串，用于去重与存储。

    - 小写
    - 统一修饰键别名（control/meta/super -> ctrl/win）
    - 修饰键按 ctrl, alt, shift, win 排序并去重
    """
    text = key.strip()
    if not text:
        return ""

    modifiers: list[str] = []
    others: list[str] = []
    for raw in text.split("+"):
        token = raw.strip().lower()
        if not token:
            continue
        alias = _MODIFIER_ALIASES.get(token)
        if alias is not None:
            if alias not in modifiers:
                modifiers.append(alias)
        else:
            canonical = _canonical_key(token) or token
            if canonical not in others:
                others.append(canonical)

    modifiers.sort(key=MODIFIER_ORDER.index)
    return "+".join(modifiers + others)


def is_modifier_only(key: str) -> bool:
    parts = [part for part in key.split("+") if part]
    return bool(parts) and all(part in _MODIFIER_ALIASES for part in parts)


def sorted_modifiers(modifiers: Iterable[str]) -> list[str]:
    unique = {modifier for modifier in modifiers if modifier in MODIFIER_ORDER}
    return sorted(unique, key=MODIFIER_ORDER.index)
