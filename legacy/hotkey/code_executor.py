"""安全代码执行器 - AST白名单 + compile缓存 + 受限exec。

替换裸 exec() 为受控的安全沙箱。
"""

import ast
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger('HotKey.CodeExecutor')


class CodeExecutor:
    """安全的代码执行器。

    特性：
    - AST 白名单检查：阻止导入危险模块、调用禁止函数
    - compile() 缓存：避免重复编译
    - 受限 exec()：传入安全命名空间
    """

    _SAFE_BUILTINS = {
        'print': print, 'len': len, 'range': range, 'int': int,
        'str': str, 'float': float, 'bool': bool, 'list': list,
        'dict': dict, 'tuple': tuple, 'set': set, 'type': type,
        'True': True, 'False': False, 'None': None,
        'abs': abs, 'min': min, 'max': max, 'sum': sum,
        'round': round, 'sorted': sorted, 'enumerate': enumerate,
        'zip': zip, 'map': map, 'filter': filter, 'isinstance': isinstance,
    }

    _FORBIDDEN_NAMES = {
        '__import__', 'eval', 'exec', 'compile', 'open',
        'getattr', 'setattr', 'delattr', 'hasattr',
        'globals', 'locals', 'vars', 'dir',
    }

    _ALLOWED_MODULES = {
        'pyautogui', 'time', 'datetime', 'math', 'random', 'json', 're',
    }

    def __init__(self, extra_modules: Optional[Dict[str, Any]] = None):
        self._code_cache: Dict[str, Any] = {}
        self._extra_modules = extra_modules or {}

    def clear_cache(self) -> None:
        """清空编译缓存。"""
        self._code_cache.clear()

    @classmethod
    def validate(cls, code_list: List[str]) -> List[str]:
        """验证代码列表安全性，返回警告列表（空列表表示安全）。"""
        warnings = []
        for i, code in enumerate(code_list):
            code_stripped = code.strip()
            if not code_stripped:
                continue
            try:
                tree = ast.parse(code_stripped)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        if isinstance(node, ast.Import):
                            modules = [alias.name for alias in node.names]
                        else:
                            modules = [node.module] if node.module else []
                        for mod in modules:
                            base_mod = mod.split('.')[0]
                            if base_mod not in cls._ALLOWED_MODULES:
                                warnings.append(
                                    f"第{i+1}行: 不允许导入模块 '{mod}'"
                                )
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            if node.func.id in cls._FORBIDDEN_NAMES:
                                warnings.append(
                                    f"第{i+1}行: 禁止调用 '{node.func.id}()'"
                                )
                    if isinstance(node, ast.Attribute):
                        if node.attr.startswith('__') and node.attr.endswith('__'):
                            if node.attr not in ('__name__', '__doc__'):
                                warnings.append(
                                    f"第{i+1}行: 禁止访问 '{node.attr}'"
                                )
            except SyntaxError as e:
                warnings.append(f"第{i+1}行: 语法错误 - {e}")
        return warnings

    def _build_safe_globals(self) -> Dict[str, Any]:
        """构建受限全局命名空间。"""
        safe_globals = {'__builtins__': self._SAFE_BUILTINS}
        # 注入额外模块
        safe_globals.update(self._extra_modules)
        # 注入标准允许模块
        import time as time_module
        safe_globals['time'] = time_module
        try:
            import pyautogui
            safe_globals['pyautogui'] = pyautogui
        except ImportError:
            pass
        return safe_globals

    def execute(self, code_list: List[str]) -> None:
        """在受限沙箱中执行代码列表。"""
        safe_globals = self._build_safe_globals()
        safe_locals: Dict[str, Any] = {}

        for code in code_list:
            code_stripped = code.strip()
            if not code_stripped:
                continue
            try:
                if code_stripped not in self._code_cache:
                    self._code_cache[code_stripped] = compile(
                        code_stripped, '<hotkey>', 'exec'
                    )
                exec(self._code_cache[code_stripped], safe_globals, safe_locals)
            except Exception as e:
                logger.error("代码执行失败 [%s]: %s", code_stripped[:60], e, exc_info=True)
