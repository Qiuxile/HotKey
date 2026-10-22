"""生成可以脱离 HotKey 直接运行的 Python 文件。"""

from __future__ import annotations

from hotkey.core import blocks as block_ops
from hotkey.core.models import Block

HEADER = '''"""由 HotKey 生成的自动化脚本。

用法:
    python 本文件.py

依赖:
    pip install pyautogui

说明:
    函数定义会放在文件前部，其余积木放进 main()，因此可以直接运行。
    需要热键触发时，仍然使用 HotKey 应用本身。
"""

import json
import math
import random
import re
import time

import pyautogui
'''


def render_program(blocks: list[Block]) -> str:
    functions = [block for block in blocks if block.kind == "logic_func_def"]
    flow = [block for block in blocks if block.kind != "logic_func_def"]

    parts = [HEADER.rstrip()]

    function_code = [
        code
        for code in (block_ops.block_code(block) for block in functions)
        if code.strip()
    ]
    if function_code:
        parts.append("\n\n".join(function_code))

    flow_code = [
        code
        for code in (block_ops.block_code(block) for block in flow)
        if code.strip()
    ]
    body = "\n".join(flow_code).strip("\n") or "pass"
    indented = "\n".join(
        "    " + line if line.strip() else "" for line in body.splitlines()
    )
    parts.append("def main():\n" + indented)
    parts.append('if __name__ == "__main__":\n    main()')

    return "\n\n".join(parts) + "\n"
