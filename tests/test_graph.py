
from unittest.mock import patch

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agent.graph import build_graph
from app.agent.state import create_initial_state


def test_graph_approval_rejection_and_resume():
    proposal_count = {"value": 0}

    def mock_fetch(state):
        return {
            "code_contents": {"main.py": "print('hello')"}
        }

    def mock_lint(state):
        return {
            "lint_errors": {"main.py": "Formatting issue"}
        }

    def mock_propose(state):
        proposal_count["value"] += 1
        return {
            "refactored_code": {
                "main.py": "print('Hello!')"
            }
        }

    def mock_apply(state):
        return {
            "history": state.get("history", []) + [
                {
                    "action": "apply_changes",
                    "status": "success",
                    "commit_sha": "test123",
                }
            ]
        }

    with (
        patch("app.agent.graph.fetch_pr_node", side_effect=mock_fetch),
        patch("app.agent.graph.lint_code_node", side_effect=mock_lint),
        patch("app.agent.graph.propose_refactor_node", side_effect=mock_propose),
        patch("app.agent.graph.apply_changes_node", side_effect=mock_apply),
    ):
        graph = build_graph(checkpointer=MemorySaver())

        config = {
            "configurable": {
                "thread_id": "graph-test-1"
            }
        }

        initial_state = create_initial_state(
            "https://github.com/user/project/pull/1"
        )

        # First execution pauses for human review.
        result = graph.invoke(initial_state, config)

        assert result.get("__interrupt__")
        assert proposal_count["value"] == 1

        # Reject the first proposal and provide feedback.
        result = graph.invoke(
            Command(
                resume={
                    "is_approved": False,
                    "reviewer_feedback": "Improve variable naming."
                }
            ),
            config,
        )

        # The graph should generate another proposal and pause again.
        assert result.get("__interrupt__")
        assert proposal_count["value"] == 2

        # Approve the second proposal.
        result = graph.invoke(
            Command(
                resume={
                    "is_approved": True,
                    "reviewer_feedback": ""
                }
            ),
            config,
        )

        # The graph must pause before applying changes.
        snapshot = graph.get_state(config)
        assert snapshot.next == ("apply_changes_node",)

        # Resume execution beyond the apply-node interruption.
        result = graph.invoke(None, config)

        final_state = graph.get_state(config).values

        assert final_state["is_approved"] is True
        assert final_state["history"][-1]["action"] == "apply_changes"
        assert final_state["history"][-1]["commit_sha"] == "test123"
        assert proposal_count["value"] == 2
