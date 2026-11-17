
from app.tools.linter_tool import run_linter_tool


def test_linter_identifies_style_issues():

    code = """
def add(a,b):
    x=10
    return a+b
"""

    result = run_linter_tool.invoke({
        "code_string": code
    })

    assert "Command: flake8" in result
    assert "Command: black" in result


def test_linter_handles_valid_code():

    code = """
def add(a, b):
    return a + b
"""

    result = run_linter_tool.invoke({
        "code_string": code
    })

    assert "Exit code: 0" in result


def test_linter_handles_syntax_error():

    code = """
def add(a, b)
    return a + b
"""

    result = run_linter_tool.invoke({
        "code_string": code
    })

    assert "E999" in result or "invalid syntax" in result.lower()
