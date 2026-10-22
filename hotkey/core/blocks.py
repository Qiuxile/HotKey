"""积木 -> Python 脚本的代码生成。"""

from __future__ import annotations

from hotkey.core import catalog
from hotkey.core.models import Block


def _body_code(children: list[Block]) -> str:
    child_codes = [block_code(child) for child in children]
    lines = [
        line
        for child_code in child_codes
        if child_code
        for line in child_code.splitlines()
    ]
    if not lines:
        return catalog.INDENT + "pass"
    return "\n".join(catalog.INDENT + line for line in lines)


def block_code(block: Block) -> str:
    """把单个积木转成代码；无法识别时返回空串。"""
    if block.kind == "empty":
        text = block.text.strip()
        return "" if text in ("", "空") else text

    try:
        snippet = catalog.snippet(block.kind)
    except KeyError:
        return ""

    code = snippet.code_for_values(block.params)
    if not code:
        return ""

    if not snippet.block:
        return code

    then_body = _body_code(block.children)
    if len(snippet.slots) >= 2 and block.else_children:
        else_body = _body_code(block.else_children)
        return f"{code}\n{then_body}\nelse:\n{else_body}"
    return f"{code}\n{then_body}"


def blocks_to_code(blocks: list[Block]) -> str:
    parts = [block_code(block) for block in blocks]
    return "\n".join(part for part in parts if part)
