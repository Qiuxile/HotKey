"""HotKey 统一常量配置。"""

# ============================================================
# 键名映射：Tkinter keysym → keyboard 库可识别的键名
# ============================================================
KEY_NAME_MAP = {
    'return': 'enter',   'space': 'space',   'tab': 'tab',
    'escape': 'esc',     'backspace': 'backspace', 'delete': 'delete',
    'insert': 'insert',  'home': 'home',     'end': 'end',
    'pageup': 'page_up', 'pagedown': 'page_down',
    'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
    'f1': 'f1', 'f2': 'f2', 'f3': 'f3', 'f4': 'f4',
    'f5': 'f5', 'f6': 'f6', 'f7': 'f7', 'f8': 'f8',
    'f9': 'f9', 'f10': 'f10', 'f11': 'f11', 'f12': 'f12',
}

# 修饰键位掩码映射
MODIFIER_MASKS = {0x0004: 'ctrl', 0x0001: 'shift', 0x20000: 'alt', 0x0040: 'win'}

# 单独的修饰键 keysym 集合
MODIFIER_KEYSYMS = {
    'Control_L', 'Control_R', 'Shift_L', 'Shift_R',
    'Alt_L', 'Alt_R', 'Meta_L', 'Meta_R',
}

# ============================================================
# 窗口尺寸常量
# ============================================================
DEFAULT_WINDOW_WIDTH = 370
DEFAULT_WINDOW_HEIGHT = 560
EDITOR_PANEL_WIDTH = 750

# ============================================================
# 主题色常量
# ============================================================
COLOR_BG_MAIN      = '#f0f3f7'   # 主背景
COLOR_BG_SIDEBAR   = '#e2e6ed'   # 侧栏/语句栏背景
COLOR_BG_HEADER    = '#3b4a5e'   # 表头背景
COLOR_BG_EDITOR    = '#1e2733'   # 代码编辑器背景
COLOR_BG_SEARCH    = '#ffffff'   # 搜索栏背景
COLOR_FG_PRIMARY   = '#1a2332'   # 主文字
COLOR_FG_HEADER    = '#ffffff'   # 表头文字
COLOR_FG_EDITOR    = '#c8d6e5'   # 编辑器文字
COLOR_FG_PLACEHOLDER = '#a0aab4' # 占位符文字
COLOR_ACCENT       = '#4a8fe7'   # 主题强调色
COLOR_ACCENT_HOVER = '#3a7bd5'   # 悬停
COLOR_SELECTION    = '#d0dff5'   # 选中行背景
COLOR_ROW_ALT      = '#f7f9fc'   # 交替行背景
COLOR_BORDER       = '#d5dce6'   # 边框色
COLOR_BUTTON       = '#4a8fe7'   # 按钮背景
COLOR_BUTTON_TEXT  = '#ffffff'   # 按钮文字
COLOR_SHADOW       = '#00000018' # 搜索栏阴影

# ============================================================
# 搜索动画参数
# ============================================================
SEARCH_DEBOUNCE_MS  = 150
ANIMATION_STEP_PX   = 10
ANIMATION_INTERVAL_MS = 16
SEARCH_HIDDEN_Y     = -40
ANIMATION_EASING    = 0.22   # 缓动系数
