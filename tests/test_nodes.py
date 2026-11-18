
from unittest.mock import patch
from app.agent.nodes import lint_code_node


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
