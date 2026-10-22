"""生成可直接运行的 Python 文件。"""

from hotkey.core.models import Block
from hotkey.core.program import render_program


def test_program_has_header_main_and_functions():
    blocks = [
        Block(
            "logic_func_def",
            params={"name": "double", "params": "x", "result": "x * 2"},
            children=[Block("logic_set", params={"name": "y", "value": "1"})],
        ),
        Block("logic_func_call", params={"name": "double", "args": "3", "variable": "r"}),
        Block("mouse_click"),
    ]

    program = render_program(blocks)

    assert "import pyautogui" in program
    assert "def double(x):" in program
    assert "return x * 2" in program
    assert program.index("def double") < program.index("def main")
    assert "r = double(3)" in program
    assert 'if __name__ == "__main__":' in program
    compile(program, "<program>", "exec")


def test_program_without_flow_uses_pass():
    blocks = [Block("logic_func_def", params={"name": "noop", "params": "", "result": ""})]

    program = render_program(blocks)

    assert "def main():\n    pass" in program
    compile(program, "<program>", "exec")


def test_program_only_flow():
    program = render_program([Block("mouse_click")])

    assert "def main():\n    pyautogui.click()" in program
    compile(program, "<program>", "exec")
