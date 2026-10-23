"""HotKey v2 入口。

用法:
    python main.py              # 编辑器
    python main.py --listen     # 后台监听器（托盘）
    python main.py --self-test  # 启动后自动退出
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="HotKey",
        description="拖拽式全局热键自动化工具",
    )
    parser.add_argument(
        "--listen",
        action="store_true",
        help="启动后台监听器（托盘），不打开编辑器窗口",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="启动后立即退出（冒烟测试用）",
    )
    args = parser.parse_args(argv)

    if args.listen:
        from hotkey.listener import run_listener

        return run_listener(self_test=args.self_test)

    # 延迟导入，保证 --help 不触发 Qt 初始化
    from hotkey.app import run

    return run(self_test=args.self_test)


if __name__ == "__main__":
    sys.exit(main())
