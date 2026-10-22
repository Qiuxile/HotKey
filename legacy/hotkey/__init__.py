"""HotKey - 热键配置与监听工具包。"""

from hotkey.models import HotKeyEntry
from hotkey.config import KEY_NAME_MAP, MODIFIER_MASKS, MODIFIER_KEYSYMS

__all__ = ['HotKeyEntry', 'KEY_NAME_MAP', 'MODIFIER_MASKS', 'MODIFIER_KEYSYMS']
