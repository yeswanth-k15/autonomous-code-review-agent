
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

import subprocess
from unittest.mock import patch


def test_linter_handles_missing_docker():
    with patch("app.tools.linter_tool.shutil.which", return_value=None):
        result = run_linter_tool.invoke({
            "code_string": "print('hello')"
        })

    assert "Docker CLI is not installed" in result


def test_linter_handles_docker_execution_failure():
    failed_result = subprocess.CompletedProcess(
        args=["docker", "run"],
        returncode=125,
        stdout="",
        stderr="Docker daemon unavailable",
    )

    with patch(
        "app.tools.linter_tool.subprocess.run",
        return_value=failed_result,
    ):
        result = run_linter_tool.invoke({
            "code_string": "print('hello')"
        })

    assert "Exit code: 125" in result
    assert "Docker daemon unavailable" in result


def test_linter_handles_timeout():
    with patch(
        "app.tools.linter_tool.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd=["docker", "run"],
            timeout=30,
        ),
    ):
        result = run_linter_tool.invoke({
            "code_string": "print('hello')"
        })

    assert "Docker linting timed out" in result
