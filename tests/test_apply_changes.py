
from unittest.mock import patch

import pytest

from app.agent.nodes import apply_changes_node


def create_state(is_approved):
    return {
        "pr_url": "https://github.com/user/project/pull/1",
        "code_contents": {
            "main.py": "print('Hello World')"
        },
        "lint_errors": {},
        "refactored_code": {
            "main.py": "print('Hello, World!')"
        },
        "is_approved": is_approved,
        "reviewer_feedback": "",
        "history": []
    }


def test_apply_changes_when_approved():
    state = create_state(True)

    with patch(
        "app.agent.nodes.commit_refactored_files",
        return_value="abc123"
    ) as mock_commit:

        result = apply_changes_node(state)

    mock_commit.assert_called_once_with(
        pr_url=state["pr_url"],
        refactored_code=state["refactored_code"]
    )

    assert result["history"][-1]["action"] == "apply_changes"
    assert result["history"][-1]["status"] == "success"
    assert result["history"][-1]["commit_sha"] == "abc123"


@pytest.mark.parametrize("approval", [False, None])
def test_apply_changes_without_approval(approval):
    state = create_state(approval)

    with patch(
        "app.agent.nodes.commit_refactored_files"
    ) as mock_commit:

        result = apply_changes_node(state)

    mock_commit.assert_not_called()

    assert result["history"][-1]["action"] == "apply_changes"
    assert result["history"][-1]["status"] == "skipped"


def test_apply_changes_without_refactored_code():
    state = create_state(True)
    state["refactored_code"] = {}

    with patch(
        "app.agent.nodes.commit_refactored_files"
    ) as mock_commit:

        with pytest.raises(
            ValueError,
            match="No refactored code available to commit"
        ):
            apply_changes_node(state)

    mock_commit.assert_not_called()
