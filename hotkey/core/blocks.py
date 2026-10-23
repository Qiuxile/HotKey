"""积木 -> Python 脚本的代码生成。"""

from __future__ import annotations

from hotkey.core import catalog
from hotkey.core.models import Block


def _assigned_variables(children: list[Block]) -> set[str]:
    """收集函数体里赋值的变量名，用于生成 global 声明。"""
    names: set[str] = set()
    assignment_kinds = {
        "logic_set",
        "logic_change",
        "logic_compare",
        "logic_math",
        "logic_random",
        "logic_func_call",
        "logic_exists",
        "logic_locate",
        "logic_pixel",
        "logic_mouse_pos",
        "logic_screen_size",
    }
    for child in children:
        if child.kind in assignment_kinds:
            name = child.params.get("name", child.params.get("variable", "")).strip()
            if name.isidentifier():
                names.add(name)
        names.update(_assigned_variables(child.children))
        names.update(_assigned_variables(child.else_children))
    return names


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


def literal_code(text: str, mode: str = "auto") -> str:
    """值槽里手填内容的 Python 形式。"""
    raw = text.strip()
    if mode in ("code", "raw"):
        return raw
    if mode == "number":
        return raw or "0"
    if mode == "bool":
        return "True" if raw.lower() in ("true", "1", "是", "真") else "False"
    if mode == "text":
        return repr(text)
    # auto：数字/布尔直接写，其余按文本加引号
    if raw in ("True", "False", "None"):
        return raw
    try:
        float(raw)
    except ValueError:
        return repr(text)
    return raw


def _format_snippet(block: Block, snippet: catalog.Snippet) -> str:
    values: dict[str, str] = {}
    for param in snippet.params:
        if param.kind == "value":
            expression = block.expressions.get(param.name)
            if expression is not None:
                values[param.name] = expression_code(expression)
            else:
                values[param.name] = literal_code(
                    block.params.get(param.name, ""),
                    block.value_modes.get(param.name, "auto"),
                )
        elif param.kind in ("number", "code"):
            values[param.name] = block.params.get(param.name, "").strip()
        elif param.kind == "key":
            values[param.name] = catalog.key_literal(
                block.params.get(param.name, "")
            )
        elif param.kind == "hotkey":
            values[param.name] = catalog.hotkey_literal(
                block.params.get(param.name, "")
            )
        else:
            values[param.name] = repr(block.params.get(param.name, ""))
    return snippet.code.format(**values)


def expression_code(block: Block | None) -> str:
    """把值积木转成表达式；空值返回空串。"""
    if block is None:
        return ""
    if block.kind == "empty":
        return block.text.strip()
    try:
        snippet = catalog.snippet(block.kind)
    except KeyError:
        return ""
    return _format_snippet(block, snippet)


def _conditional_code(block: Block, snippet: catalog.Snippet, keyword: str) -> str:
    code = _format_snippet(block, snippet)
    result = f"{code}\n{_body_code(block.children)}"

    children = list(block.else_children)
    for child in children:
        if child.kind == "flow_elif":
            result += "\n" + block_code(child)
    others = [child for child in children if child.kind != "flow_elif"]
    if others:
        result += "\nelse:\n" + _body_code(others)
    return result


def block_code(block: Block) -> str:
    """把单个积木转成代码；无法识别时返回空串。"""
    if block.kind in ("empty", "python"):
        text = block.text.strip()
        return "" if text in ("", "空") else text

    try:
        snippet = catalog.snippet(block.kind)
    except KeyError:
        return ""

    code = _format_snippet(block, snippet)
    if not code:
        return ""

    if not snippet.block:
        return code

    if block.kind == "logic_func_def":
        lines = _flatten(block.children)
        params = {
            part.strip().split("=")[0].strip()
            for part in block.params.get("params", "").split(",")
            if part.strip()
        }
        globals_ = sorted(_assigned_variables(block.children) - params)
        if globals_:
            lines.insert(0, f"global {', '.join(globals_)}")
        body = (
            "\n".join(catalog.INDENT + line for line in lines)
            if lines
            else catalog.INDENT + "pass"
        )
        return f"{code}\n{body}"

    if block.kind == "flow_if_else":
        return _conditional_code(block, snippet, "if")
    if block.kind == "flow_elif":
        return _conditional_code(block, snippet, "elif")

    then_body = _body_code(block.children)
    if len(snippet.slots) >= 2 and block.else_children:
        else_body = _body_code(block.else_children)
        return f"{code}\n{then_body}\nelse:\n{else_body}"
    return f"{code}\n{then_body}"


def blocks_to_code(blocks: list[Block]) -> str:
    parts = [block_code(block) for block in blocks]
    return "\n".join(part for part in parts if part)
