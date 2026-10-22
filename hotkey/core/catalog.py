"""操作面板语句目录（数据与 UI 分离，不依赖 Qt）。"""

from __future__ import annotations

from dataclasses import dataclass

CURSOR_MARKER = "${cursor}"
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
    """一条可拖拽的语句模板。"""

    id: str
    category: str
    label: str
    template: str
    block: bool = False

    def render(self) -> tuple[str, int | None]:
        """返回 (去掉光标标记的文本, 光标位置)。"""
        if CURSOR_MARKER not in self.template:
            return self.template, None
        offset = self.template.index(CURSOR_MARKER)
        return self.template.replace(CURSOR_MARKER, "", 1), offset


SNIPPETS: tuple[Snippet, ...] = (
    # ── 鼠标操作 ──────────────────────────────────────────────
    Snippet(
        "mouse_move_to",
        "mouse",
        "移动鼠标到 (500, 300)",
        "pyautogui.moveTo(500, 300)",
    ),
    Snippet(
        "mouse_move_rel",
        "mouse",
        "相对移动鼠标 (100, 0)",
        "pyautogui.moveRel(100, 0, duration=0.3)",
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
        "拖拽到 (800, 400)",
        "pyautogui.dragTo(800, 400, duration=0.5)",
    ),
    Snippet(
        "mouse_position",
        "mouse",
        "读取当前鼠标坐标到 x, y",
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
        "输入文本",
        "pyautogui.typewrite('${cursor}')",
    ),
    Snippet(
        "key_type_interval",
        "keyboard",
        "逐字输入文本（间隔 0.1 秒）",
        "pyautogui.typewrite('${cursor}', interval=0.1)",
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
        "截取区域 (0, 0, 300, 400)",
        "pyautogui.screenshot('region.png', region=(0, 0, 300, 400))",
    ),
    Snippet(
        "screen_size",
        "screen",
        "读取屏幕尺寸到 w, h",
        "w, h = pyautogui.size()",
    ),
    Snippet(
        "screen_locate",
        "screen",
        "在屏幕上查找图片",
        "pyautogui.locateOnScreen('target.png')",
    ),
    Snippet(
        "screen_locate_center",
        "screen",
        "查找图片并取中心坐标",
        "pyautogui.locateCenterOnScreen('target.png')",
    ),
    Snippet(
        "screen_pixel",
        "screen",
        "读取像素颜色到 (500, 300)",
        "pyautogui.pixel(500, 300)",
    ),
    Snippet(
        "screen_pixel_matches",
        "screen",
        "判断像素是否为白色",
        "pyautogui.pixelMatchesColor(500, 300, (255, 255, 255))",
    ),
    # ── 弹窗交互 ──────────────────────────────────────────────
    Snippet(
        "dialog_alert",
        "dialog",
        "弹出信息提示框",
        "pyautogui.alert('${cursor}')",
    ),
    Snippet(
        "dialog_confirm",
        "dialog",
        "弹出确认对话框",
        "pyautogui.confirm('是否继续？')",
    ),
    Snippet(
        "dialog_prompt",
        "dialog",
        "弹出文本输入框",
        "pyautogui.prompt('请输入：')",
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
        f"for i in range(3):\n{INDENT}{CURSOR_MARKER}",
        block=True,
    ),
    Snippet(
        "flow_if",
        "flow",
        "条件判断分支",
        f"if True:\n{INDENT}{CURSOR_MARKER}",
        block=True,
    ),
)

_BY_ID = {snippet.id: snippet for snippet in SNIPPETS}


def snippet(snippet_id: str) -> Snippet:
    return _BY_ID[snippet_id]


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
