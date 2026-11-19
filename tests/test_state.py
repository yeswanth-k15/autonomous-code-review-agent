
from app.agent.state import create_initial_state


def test_create_initial_state():

    state = create_initial_state(
        "https://github.com/user/project/pull/1"
    )

    assert state["pr_url"] == "https://github.com/user/project/pull/1"

    assert state["head_sha"] == ""

    assert state["code_contents"] == {}

    assert state["lint_errors"] == {}

    assert state["refactored_code"] == {}

    assert state["is_approved"] is None

    assert state["reviewer_feedback"] == ""

    assert state["history"] == []
