"""旧版 Tk 入口（迁移期保留，v2 功能对齐后删除）。

代码位于 legacy/ 目录，仅在需要对比旧行为时运行:
    python main_tk.py
"""

from __future__ import annotations

import os
import sys

_LEGACY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy")
sys.path.insert(0, _LEGACY_DIR)

from hotkey.app import App  # noqa: E402  （导入的是 legacy/hotkey）


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
