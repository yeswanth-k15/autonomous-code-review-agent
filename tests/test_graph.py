import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
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

def test_sqlite_checkpoint_persists_after_graph_restart(tmp_path):
    database_path = tmp_path / "review_checkpoints.sqlite"

    def mock_fetch(state):
        return {
            "code_contents": {"main.py": "print('hello')"},
            "head_sha": "test-head-sha",
        }

    def mock_lint(state):
        return {
            "lint_errors": {"main.py": "Formatting issue"}
        }

    def mock_propose(state):
        return {
            "refactored_code": {
                "main.py": "print('Hello!')"
            }
        }

    config = {
        "configurable": {
            "thread_id": "sqlite-persistence-test"
        }
    }

    with (
        patch("app.agent.graph.fetch_pr_node", side_effect=mock_fetch),
        patch("app.agent.graph.lint_code_node", side_effect=mock_lint),
        patch("app.agent.graph.propose_refactor_node", side_effect=mock_propose),
    ):
        # First graph: save review state to SQLite.
        connection1 = sqlite3.connect(
            str(database_path),
            check_same_thread=False,
        )

        checkpointer1 = SqliteSaver(connection1)
        checkpointer1.setup()

        graph1 = build_graph(checkpointer=checkpointer1)

        initial_state = create_initial_state(
            "https://github.com/user/project/pull/1"
        )

        result = graph1.invoke(initial_state, config)

        assert result.get("__interrupt__")

        saved_state = graph1.get_state(config).values

        assert saved_state["code_contents"] == {
            "main.py": "print('hello')"
        }
        assert saved_state["refactored_code"] == {
            "main.py": "print('Hello!')"
        }

        connection1.close()

        # Second graph: reopen the same SQLite database.
        connection2 = sqlite3.connect(
            str(database_path),
            check_same_thread=False,
        )

        checkpointer2 = SqliteSaver(connection2)
        checkpointer2.setup()

        graph2 = build_graph(checkpointer=checkpointer2)

        restored_state = graph2.get_state(config)

        assert restored_state.values["pr_url"] == initial_state["pr_url"]
        assert restored_state.values["code_contents"] == saved_state["code_contents"]
        assert restored_state.values["refactored_code"] == saved_state["refactored_code"]

        # The graph should still be waiting for human approval.
        assert restored_state.next == ("approval_node",)

        connection2.close()
