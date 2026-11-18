
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

from app.agent.nodes import propose_refactor_node


def test_propose_refactor_node():
    state = {
        "pr_url": "https://github.com/user/project/pull/1",
        "code_contents": {
            "main.py": "print('Hello World')",
            "utils.py": "def add(a, b): return a + b"
        },
        "lint_errors": {
            "main.py": "Formatting issue",
            "utils.py": "Line too long"
        },
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": "Improve readability",
        "history": []
    }

    mock_llm = MagicMock()

    mock_llm.invoke.side_effect = [
        SimpleNamespace(content="print('Hello, World!')"),
        SimpleNamespace(content="def add(a, b):\n    return a + b")
    ]

    with patch(
        "app.agent.nodes.ChatOpenAI",
        return_value=mock_llm
    ) as mock_chat:

        result = propose_refactor_node(state)

    assert mock_chat.called
    assert mock_chat.call_args.kwargs["model"] == "gpt-4o-mini"

    assert len(result["refactored_code"]) == 2

    assert result["refactored_code"]["main.py"] == (
        "print('Hello, World!')"
    )

    assert result["refactored_code"]["utils.py"] == (
        "def add(a, b):\n    return a + b"
    )

    assert result["history"][-1]["action"] == "propose_refactor"
    assert result["history"][-1]["status"] == "success"

    assert mock_llm.invoke.call_count == 2

    first_prompt = mock_llm.invoke.call_args_list[0].args[0]
    human_message = first_prompt[1]

    assert "Improve readability" in human_message.content


def test_propose_refactor_node_without_code():
    state = {
        "pr_url": "https://github.com/user/project/pull/1",
        "code_contents": {},
        "lint_errors": {},
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": "",
        "history": []
    }

    with patch("app.agent.nodes.ChatOpenAI") as mock_chat:
        with pytest.raises(
            ValueError,
            match="No Python code available to refactor"
        ):
            propose_refactor_node(state)

    mock_chat.assert_not_called()
