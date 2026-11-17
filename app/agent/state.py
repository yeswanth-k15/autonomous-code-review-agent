
from typing import TypedDict


class ReviewState(TypedDict):
    """
    Shared state for the Autonomous Code Review Agent.

    Every LangGraph node reads from this state
    and returns updates to it.
    """

    # GitHub Pull Request URL
    pr_url: str

    # Original source code retrieved from the PR
    code_contents: dict[str, str]

    # Errors detected by linting tools
    lint_errors: dict[str, str]

    # AI-generated refactored code
    refactored_code: dict[str, str]

    # Human review decision
    is_approved: bool | None

    # Feedback provided by the reviewer
    reviewer_feedback: str

    # History of agent activities
    history: list[dict[str, str]]


def create_initial_state(pr_url: str) -> ReviewState:
    """
    Creates the initial state for a new PR review.
    """

    return {
        "pr_url": pr_url,
        "code_contents": {},
        "lint_errors": {},
        "refactored_code": {},
        "is_approved": None,
        "reviewer_feedback": "",
        "history": [],
    }
