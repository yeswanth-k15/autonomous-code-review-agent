
from unittest.mock import patch

import pytest

from app.agent.nodes import fetch_pr_node, lint_code_node


def test_fetch_pr_node():
    state = {
        "pr_url": "https://github.com/user/project/pull/1",
        "head_sha": "",
        "code_contents": {},
        "lint_errors": {},
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": "",
        "history": [],
    }

    expected_code = {
        "main.py": "print('Hello World')"
    }

    with patch(
        "app.agent.nodes.fetch_pull_request_data",
        return_value=(expected_code, "test-commit-sha"),
    ) as mock_fetch:

        result = fetch_pr_node(state)

    mock_fetch.assert_called_once_with(state["pr_url"])

    assert result["code_contents"] == expected_code
    assert result["head_sha"] == "test-commit-sha"
    assert result["history"][-1]["action"] == "fetch_pr"
    assert result["history"][-1]["status"] == "success"


def test_fetch_pr_node_without_python_files():
    state = {
        "pr_url": "https://github.com/user/project/pull/1",
        "head_sha": "",
        "code_contents": {},
        "lint_errors": {},
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": "",
        "history": [],
    }

    with patch(
        "app.agent.nodes.fetch_pull_request_data",
        return_value=({}, "test-commit-sha"),
    ) as mock_fetch:

        with pytest.raises(
            ValueError,
            match="No eligible Python files found",
        ):
            fetch_pr_node(state)

    mock_fetch.assert_called_once_with(state["pr_url"])


def test_lint_code_node():
    state = {
        "pr_url": "https://github.com/user/project/pull/1",
        "code_contents": {
            "main.py": "print('Hello World')",
            "utils.py": "def add(a, b): return a + b"
        },
        "lint_errors": {},
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": "",
        "history": []
    }

    with patch("app.agent.nodes.run_linter_tool") as mock_linter:
        mock_linter.invoke.return_value = "No linting errors"

        result = lint_code_node(state)

    assert len(result["lint_errors"]) == 2
    assert result["lint_errors"]["main.py"] == "No linting errors"
    assert result["lint_errors"]["utils.py"] == "No linting errors"
    assert result["history"][-1]["action"] == "lint_code"
    assert mock_linter.invoke.call_count == 2
