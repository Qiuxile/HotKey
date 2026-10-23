"""生成可直接运行的 Python 文件。"""

from hotkey.core.models import Block
from hotkey.core.program import render_program


def test_program_has_header_main_and_functions():
    blocks = [
        Block(
            "logic_func_def",
            params={"name": "double", "params": "x"},
            children=[
                Block("logic_set", params={"name": "y", "value": "1"}, value_modes={"value": "number"}),
                Block("flow_return", params={"value": "x * 2"}, value_modes={"value": "code"}),
            ],
        ),
        Block(
            "logic_set",
            params={"name": "r", "value": ""},
            expressions={
                "value": Block(
                    "value_func_call",
                    params={"name": "double", "args": "3"},
                )
            },
        ),
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
    blocks = [Block("logic_func_def", params={"name": "noop", "params": ""})]

    program = render_program(blocks)

    assert "def main():\n    pass" in program
    compile(program, "<program>", "exec")


def test_program_only_flow():
    program = render_program([Block("mouse_click")])

    assert "def main():\n    pyautogui.click()" in program
    compile(program, "<program>", "exec")
