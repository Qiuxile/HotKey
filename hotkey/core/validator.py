"""脚本安全校验与执行命名空间（不依赖 Qt）。"""

from __future__ import annotations

import ast
import importlib
from types import CodeType
from typing import Any

from hotkey.core.models import Issue, IssueLevel

ALLOWED_MODULES = frozenset(
    {"pyautogui", "time", "datetime", "math", "random", "json", "re"}
)

FORBIDDEN_CALLS = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "open",
        "__import__",
        "getattr",
        "setattr",
        "delattr",
        "globals",
        "locals",
        "vars",
        "input",
        "breakpoint",
        "exit",
        "quit",
    }
)

# 允许被脚本访问的 dunder 名称；其余一律拒绝
ALLOWED_DUNDERS = frozenset({"__name__", "__doc__"})

SAFE_BUILTINS: dict[str, Any] = {
    "print": print,
    "len": len,
    "range": range,
    "int": int,
    "str": str,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "set": set,
    "type": type,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "round": round,
    "sorted": sorted,
    "enumerate": enumerate,
    "zip": zip,
    "map": map,
    "filter": filter,
    "isinstance": isinstance,
    "repr": repr,
    "reversed": reversed,
    "format": format,
    "all": all,
    "any": any,
    "Exception": Exception,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "True": True,
    "False": False,
    "None": None,
}


def _base_module(name: str) -> str:
    return name.split(".")[0]


def validate(script: str) -> list[Issue]:
    """校验整段脚本，返回问题列表（空列表表示没有发现问题）。"""
    if not script.strip():
        return []

    try:
        tree = ast.parse(script)
    except SyntaxError as exc:
        return [
            Issue(
                IssueLevel.ERROR,
                f"语法错误: {exc.msg}",
                exc.lineno or 1,
            )
        ]

    issues: list[Issue] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _base_module(alias.name) not in ALLOWED_MODULES:
                    issues.append(
                        Issue(
                            IssueLevel.ERROR,
                            f"不允许导入模块 '{alias.name}'",
                            node.lineno,
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                issues.append(
                    Issue(IssueLevel.ERROR, "不允许相对导入", node.lineno)
                )
                continue
            module = node.module or ""
            if _base_module(module) not in ALLOWED_MODULES:
                issues.append(
                    Issue(
                        IssueLevel.ERROR,
                        f"不允许导入模块 '{module}'",
                        node.lineno,
                    )
                )
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in FORBIDDEN_CALLS:
                issues.append(
                    Issue(
                        IssueLevel.ERROR,
                        f"禁止调用 '{func.id}()'",
                        node.lineno,
                    )
                )
        elif isinstance(node, ast.Attribute):
            if (
                node.attr.startswith("__")
                and node.attr.endswith("__")
                and node.attr not in ALLOWED_DUNDERS
            ):
                issues.append(
                    Issue(
                        IssueLevel.ERROR,
                        f"禁止访问属性 '{node.attr}'",
                        node.lineno,
                    )
                )

    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(issue.level is IssueLevel.ERROR for issue in issues)


def _safe_import(
    name: str,
    globals_: dict[str, Any] | None = None,
    locals_: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> Any:
    if level:
        raise ImportError("不允许相对导入")
    root = _base_module(name)
    if root not in ALLOWED_MODULES:
        raise ImportError(f"不允许导入模块 '{name}'")
    return importlib.import_module(name)


def build_namespace() -> dict[str, Any]:
    """构造脚本执行用的命名空间。

    白名单模块在这里统一注入，校验与执行共用同一份来源，避免出现
    "校验通过但运行时报 NameError" 的不一致。
    """
    builtins = dict(SAFE_BUILTINS)
    builtins["__import__"] = _safe_import
    namespace: dict[str, Any] = {
        "__builtins__": builtins,
        "__name__": "__hotkey__",
    }

    for name in ALLOWED_MODULES:
        try:
            namespace[name] = importlib.import_module(name)
        except ImportError:
            continue

    return namespace


def compile_script(script: str, filename: str = "<hotkey>") -> CodeType:
    """整段编译脚本。

    与旧版逐行编译不同，这里保留缩进和块结构，``for`` / ``if`` 才能真正执行。
    """
    return compile(script, filename, "exec")
