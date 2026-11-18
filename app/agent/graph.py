
import os
import sqlite3

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from app.agent.state import ReviewState
from app.agent.nodes import (
    fetch_pr_node,
    lint_code_node,
    propose_refactor_node,
    apply_changes_node,
)

load_dotenv()


def approval_node(state: ReviewState) -> dict:
    """
    Pause the workflow and request a human review decision.
    """

    review_response = interrupt({
        "message": "Please review the proposed code changes.",
        "pr_url": state["pr_url"],
        "files": list(state.get("refactored_code", {}).keys()),
    })

    if not isinstance(review_response, dict):
        raise ValueError("Review response must be a dictionary.")

    is_approved = review_response.get("is_approved")

    if not isinstance(is_approved, bool):
        raise ValueError(
            "Review response must contain a boolean is_approved value."
        )

    reviewer_feedback = review_response.get(
        "reviewer_feedback", ""
    )

    if not isinstance(reviewer_feedback, str):
        raise ValueError("Reviewer feedback must be a string.")

    return {
        "is_approved": is_approved,
        "reviewer_feedback": reviewer_feedback,
        "history": state.get("history", []) + [
            {
                "action": "human_review",
                "status": "approved" if is_approved else "rejected",
            }
        ],
    }


def route_after_review(state: ReviewState) -> str:
    """
    Decide the next node based on the reviewer's decision.
    """

    if state.get("is_approved") is True:
        return "approved"

    return "rejected"


def build_graph(checkpointer=None):
    """
    Build and compile the complete code review workflow.

    Uses SQLite persistence by default. Tests can inject
    an alternative checkpointer.
    """

    workflow = StateGraph(ReviewState)

    workflow.add_node("fetch_pr_node", fetch_pr_node)
    workflow.add_node("lint_code_node", lint_code_node)
    workflow.add_node("propose_refactor_node", propose_refactor_node)
    workflow.add_node("approval_node", approval_node)
    workflow.add_node("apply_changes_node", apply_changes_node)

    workflow.add_edge(START, "fetch_pr_node")
    workflow.add_edge("fetch_pr_node", "lint_code_node")
    workflow.add_edge("lint_code_node", "propose_refactor_node")
    workflow.add_edge("propose_refactor_node", "approval_node")

    workflow.add_conditional_edges(
        "approval_node",
        route_after_review,
        {
            "approved": "apply_changes_node",
            "rejected": "propose_refactor_node",
        },
    )

    workflow.add_edge("apply_changes_node", END)

    if checkpointer is None:
        database_path = os.getenv(
            "CHECKPOINT_DB_PATH",
            "checkpoints.sqlite"
        )

        connection = sqlite3.connect(
            database_path,
            check_same_thread=False
        )

        checkpointer = SqliteSaver(connection)
        checkpointer.setup()

    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["apply_changes_node"],
    )


review_graph = build_graph()
