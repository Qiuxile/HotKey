"""操作面板积木目录：中文显示模板 + Python 代码模板（不依赖 Qt）。

每个积木用 ``label`` 展示中文，用 ``code`` 生成真正的 Python。
``label`` 里的 ``{name}`` 是用户需要填写的参数，拖入时留空。
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass

INDENT = "    "

CATEGORIES: tuple[tuple[str, str], ...] = (
    ("mouse", "🖱️ 鼠标操作"),
    ("keyboard", "⌨️ 键盘操作"),
    ("screen", "🖥️ 屏幕操作"),
    ("dialog", "💬 弹窗交互"),
    ("flow", "⏱️ 流程控制"),
)


@dataclass(frozen=True)
class Snippet:
    id: str
    category: str
    label: str
    code: str
    block: bool = False
    quoted: tuple[str, ...] = ()

    # ---------------------------------------------------------------- 参数

    def fields(self) -> tuple[str, ...]:
        return tuple(
            name
            for _, name, _, _ in string.Formatter().parse(self.label)
            if name
        )

    def blank_text(self) -> str:
        """拖入时显示的中文，参数留空。"""
        return self.label.format(**{name: "" for name in self.fields()})

    def parse(self, text: str) -> dict[str, str] | None:
        """从用户编辑后的中文里取回参数；无法识别时返回 None。"""
        fields = self.fields()
        cleaned = text.strip()

        if not fields:
            return {} if cleaned == self.label.strip() else None

        parts: list[str] = []
        for literal, name, _spec, _conversion in string.Formatter().parse(self.label):
            parts.append(re.escape(literal))
            if name:
                parts.append(f"(?P<{name}>.*?)")
        pattern = "^" + "".join(parts) + "$"

        match = re.match(pattern, cleaned, re.DOTALL)
        if not match:
            return None
        return {name: match.group(name).strip() for name in fields}

    def code_for_text(self, text: str) -> str | None:
        params = self.parse(text)
        if params is None:
            return None

        values: dict[str, str] = {}
        for name in self.fields():
            value = params.get(name, "")
            values[name] = repr(value) if name in self.quoted else value
        try:
            return self.code.format(**values)
        except (KeyError, IndexError):
            return None


SNIPPETS: tuple[Snippet, ...] = (
    # ── 鼠标操作 ──────────────────────────────────────────────
    Snippet(
        "mouse_move_to",
        "mouse",
        "移动鼠标到（{x}, {y}）",
        "pyautogui.moveTo({x}, {y})",
    ),
    Snippet(
        "mouse_move_rel",
        "mouse",
        "相对移动鼠标（{dx}, {dy}）",
        "pyautogui.moveRel({dx}, {dy}, duration=0.3)",
    ),
    Snippet("mouse_click", "mouse", "单击鼠标左键", "pyautogui.click()"),
    Snippet(
        "mouse_double_click",
        "mouse",
        "双击鼠标左键",
        "pyautogui.doubleClick()",
    ),
    Snippet(
        "mouse_right_click",
        "mouse",
        "单击鼠标右键",
        "pyautogui.click(button='right')",
    ),
    Snippet("mouse_down", "mouse", "鼠标左键按下", "pyautogui.mouseDown()"),
    Snippet("mouse_up", "mouse", "鼠标左键释放", "pyautogui.mouseUp()"),
    Snippet(
        "mouse_scroll_up",
        "mouse",
        "鼠标滚轮向上滚",
        "pyautogui.scroll(10)",
    ),
    Snippet(
        "mouse_scroll_down",
        "mouse",
        "鼠标滚轮向下滚",
        "pyautogui.scroll(-10)",
    ),
    Snippet(
        "mouse_drag",
        "mouse",
        "拖拽到（{x}, {y}）",
        "pyautogui.dragTo({x}, {y}, duration=0.5)",
    ),
    Snippet(
        "mouse_position",
        "mouse",
        "读取鼠标坐标到变量 x, y",
        "x, y = pyautogui.position()",
    ),
    # ── 键盘操作 ──────────────────────────────────────────────
    Snippet(
        "key_press_enter",
        "keyboard",
        "按下 Enter",
        "pyautogui.press('enter')",
    ),
    Snippet(
        "key_type_text",
        "keyboard",
        "输入文本「{text}」",
        "pyautogui.typewrite({text})",
        quoted=("text",),
    ),
    Snippet(
        "key_type_interval",
        "keyboard",
        "逐字输入文本「{text}」，间隔 0.1 秒",
        "pyautogui.typewrite({text}, interval=0.1)",
        quoted=("text",),
    ),
    Snippet(
        "key_hotkey_copy",
        "keyboard",
        "组合键 Ctrl+C",
        "pyautogui.hotkey('ctrl', 'c')",
    ),
    Snippet(
        "key_hotkey_paste",
        "keyboard",
        "组合键 Ctrl+V",
        "pyautogui.hotkey('ctrl', 'v')",
    ),
    Snippet(
        "key_hotkey_alt_tab",
        "keyboard",
        "组合键 Alt+Tab",
        "pyautogui.hotkey('alt', 'tab')",
    ),
    Snippet(
        "key_hotkey_win_r",
        "keyboard",
        "组合键 Win+R",
        "pyautogui.hotkey('win', 'r')",
    ),
    Snippet(
        "key_down_shift",
        "keyboard",
        "按住 Shift",
        "pyautogui.keyDown('shift')",
    ),
    Snippet(
        "key_up_shift",
        "keyboard",
        "松开 Shift",
        "pyautogui.keyUp('shift')",
    ),
    # ── 屏幕操作 ──────────────────────────────────────────────
    Snippet(
        "screen_screenshot",
        "screen",
        "截取全屏到 screenshot.png",
        "pyautogui.screenshot('screenshot.png')",
    ),
    Snippet(
        "screen_screenshot_region",
        "screen",
        "截取区域（左 {left}，上 {top}，宽 {width}，高 {height}）",
        "pyautogui.screenshot('region.png', region=({left}, {top}, {width}, {height}))",
    ),
    Snippet(
        "screen_size",
        "screen",
        "读取屏幕尺寸到变量 w, h",
        "w, h = pyautogui.size()",
    ),
    Snippet(
        "screen_locate",
        "screen",
        "在屏幕上查找图片「{image}」",
        "pyautogui.locateOnScreen({image})",
        quoted=("image",),
    ),
    Snippet(
        "screen_locate_center",
        "screen",
        "查找图片并取中心坐标「{image}」",
        "pyautogui.locateCenterOnScreen({image})",
        quoted=("image",),
    ),
    Snippet(
        "screen_pixel",
        "screen",
        "读取坐标（{x}, {y}）的颜色",
        "pyautogui.pixel({x}, {y})",
    ),
    Snippet(
        "screen_pixel_matches",
        "screen",
        "判断坐标（{x}, {y}）是否为颜色（{r}, {g}, {b}）",
        "pyautogui.pixelMatchesColor({x}, {y}, ({r}, {g}, {b}))",
    ),
    # ── 弹窗交互 ──────────────────────────────────────────────
    Snippet(
        "dialog_alert",
        "dialog",
        "弹出提示：{text}",
        "pyautogui.alert({text})",
        quoted=("text",),
    ),
    Snippet(
        "dialog_confirm",
        "dialog",
        "弹出确认框：{text}",
        "pyautogui.confirm({text})",
        quoted=("text",),
    ),
    Snippet(
        "dialog_prompt",
        "dialog",
        "弹出输入框：{text}",
        "pyautogui.prompt({text})",
        quoted=("text",),
    ),
    # ── 流程控制 ──────────────────────────────────────────────
    Snippet("flow_sleep_05", "flow", "等待 0.5 秒", "time.sleep(0.5)"),
    Snippet("flow_sleep_1", "flow", "等待 1 秒", "time.sleep(1)"),
    Snippet("flow_sleep_2", "flow", "等待 2 秒", "time.sleep(2)"),
    Snippet("flow_sleep_5", "flow", "等待 5 秒", "time.sleep(5)"),
    Snippet(
        "flow_for_3",
        "flow",
        "重复执行 3 次",
        "for i in range(3):",
        block=True,
    ),
    Snippet(
        "flow_if",
        "flow",
        "如果条件成立（True）",
        "if True:",
        block=True,
    ),
)

_BY_ID = {snippet.id: snippet for snippet in SNIPPETS}


def snippet(snippet_id: str) -> Snippet:
    return _BY_ID[snippet_id]


def is_container(snippet_id: str) -> bool:
    try:
        return snippet(snippet_id).block
    except KeyError:
        return False


def category_label(category_id: str) -> str:
    for category, label in CATEGORIES:
        if category == category_id:
            return label
    return category_id


def snippets_by_category() -> dict[str, list[Snippet]]:
    grouped: dict[str, list[Snippet]] = {category: [] for category, _ in CATEGORIES}
    for snippet_ in SNIPPETS:
        grouped.setdefault(snippet_.category, []).append(snippet_)
    return grouped
