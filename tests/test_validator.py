"""core/validator 的单元测试：整段校验与受限命名空间。"""

import pytest

from hotkey.core import validator
from hotkey.core.models import IssueLevel


def errors(script):
    return [issue for issue in validator.validate(script) if issue.level is IssueLevel.ERROR]


def test_valid_script_has_no_issues():
    script = "import math\nprint(math.sqrt(4))"
    assert validator.validate(script) == []


def test_for_loop_is_a_valid_whole_script():
    script = "total = 0\nfor i in range(3):\n    total += i"
    assert validator.validate(script) == []


def test_syntax_error_is_reported():
    issues = validator.validate("for i in range(3):")
    assert issues
    assert issues[0].level is IssueLevel.ERROR
    assert "语法错误" in issues[0].message
    assert issues[0].line == 1


def test_forbidden_import():
    issues = errors("import os")
    assert issues and "os" in issues[0].message


def test_forbidden_from_import():
    issues = errors("from subprocess import Popen")
    assert issues


def test_forbidden_call():
    issues = errors("eval('1 + 1')")
    assert issues


def test_dunder_attribute_is_rejected():
    assert errors("x = (1).__class__")
    assert errors("pyautogui.__loader__")


def test_allowed_dunder_is_permitted():
    assert validator.validate("print(__name__)") == []


def test_empty_script_is_valid():
    assert validator.validate("") == []
    assert validator.validate("   \n") == []


def test_whole_script_executes_loop():
    namespace = validator.build_namespace()
    exec(validator.compile_script("x = 0\nfor i in range(3):\n    x += i"), namespace)
    assert namespace["x"] == 3


def test_namespace_contains_whitelisted_modules():
    namespace = validator.build_namespace()
    for module in ("time", "math", "random", "json", "re", "datetime"):
        assert module in namespace


def test_restricted_import_blocks_os():
    namespace = validator.build_namespace()
    with pytest.raises(ImportError):
        exec(validator.compile_script("import os"), namespace)
