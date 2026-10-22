"""积木 -> Python 脚本的代码生成。"""

from __future__ import annotations

from hotkey.core import catalog
from hotkey.core.models import Block


def _flatten(children: list[Block]) -> list[str]:
    lines: list[str] = []
    for child in children:
        code = block_code(child)
        if code:
            lines.extend(code.splitlines())
    return lines


def _body_code(children: list[Block]) -> str:
    lines = _flatten(children)
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

    if block.kind == "logic_func_def":
        lines = _flatten(block.children)
        result = block.params.get("result", "").strip()
        if result:
            lines.append(f"return {result}")
        body = (
            "\n".join(catalog.INDENT + line for line in lines)
            if lines
            else catalog.INDENT + "pass"
        )
        return f"{code}\n{body}"

    then_body = _body_code(block.children)
    if len(snippet.slots) >= 2 and block.else_children:
        else_body = _body_code(block.else_children)
        return f"{code}\n{then_body}\nelse:\n{else_body}"
    return f"{code}\n{then_body}"


def blocks_to_code(blocks: list[Block]) -> str:
    parts = [block_code(block) for block in blocks]
    return "\n".join(part for part in parts if part)
