"""积木 -> Python 脚本的代码生成。"""

from __future__ import annotations

from hotkey.core import catalog
from hotkey.core.models import Block


def block_code(block: Block) -> str:
    """把单个积木转成代码；无法识别时返回空串。"""
    if block.kind == "empty":
        text = block.text.strip()
        return "" if text in ("", "空") else text

    try:
        snippet = catalog.snippet(block.kind)
    except KeyError:
        return ""

    code = snippet.code_for_text(block.text)
    if code is None:
        return ""

    if not snippet.block:
        return code

    child_codes = [block_code(child) for child in block.children]
    lines = [
        line
        for child_code in child_codes
        if child_code
        for line in child_code.splitlines()
    ]
    body = "\n".join(catalog.INDENT + line for line in lines)
    if not body:
        body = catalog.INDENT + "pass"
    return f"{code}\n{body}"


def blocks_to_code(blocks: list[Block]) -> str:
    parts = [block_code(block) for block in blocks]
    return "\n".join(part for part in parts if part)
