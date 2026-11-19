
import hashlib
import hmac
import json
import os

from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver
from app.agent.graph import build_graph

from main import app

client = TestClient(app)
TEST_REVIEWER_TOKEN = "test-reviewer-token-123"


def create_github_signature(payload):
    """Generate a signature for the exact HTTP request body."""

    secret = os.getenv("WEBHOOK_SECRET")

    if not secret:
        raise RuntimeError("WEBHOOK_SECRET is missing from .env")

    payload_body = json.dumps(
        payload,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    digest = hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return payload_body, f"sha256={digest}"



def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@patch("app.api.routes.review_graph.ainvoke", new_callable=AsyncMock)
def test_github_webhook(mock_ainvoke, tmp_path, monkeypatch):
    database_path = tmp_path / "test_checkpoints.sqlite"
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(database_path))
    mock_ainvoke.return_value = {
        "__interrupt__": ["waiting for review"]
    }

    payload = {
        "repository": {
            "full_name": "user/project"
        },
        "pull_request": {
            "number": 1,
            "html_url": "https://github.com/user/project/pull/1"
        }
    }

    payload_body, signature = create_github_signature(payload)
    
    response = client.post(
    	"/api/webhooks/github",
    	content=payload_body,
    	headers={
        	"Content-Type": "application/json",
        	"X-Hub-Signature-256": signature,
		"X-GitHub-Delivery": "test-delivery-001",
    	},
    )

    assert response.status_code == 200
    assert response.json()["thread_id"] == "user/project-1"
    assert response.json()["status"] == "waiting_for_review"
    mock_ainvoke.assert_called_once()


def test_github_webhook_without_pull_request():
    payload = {"action": "opened"}

    payload_body, signature = create_github_signature(payload)

    response = client.post(
    	"/api/webhooks/github",
    	content=payload_body,
    	headers={
        	"Content-Type": "application/json",
        	"X-Hub-Signature-256": signature,
    	},
     )

    assert response.status_code == 400


def test_github_webhook_without_signature():
    payload = {
        "repository": {
            "full_name": "user/project"
        },
        "pull_request": {
            "number": 1,
            "html_url": "https://github.com/user/project/pull/1"
        }
    }

    response = client.post(
        "/api/webhooks/github",
        json=payload,
    )

    assert response.status_code == 401


def test_github_webhook_with_invalid_signature():
    payload = {
        "repository": {
            "full_name": "user/project"
        },
        "pull_request": {
            "number": 1,
            "html_url": "https://github.com/user/project/pull/1"
        }
    }

    response = client.post(
        "/api/webhooks/github",
        json=payload,
        headers={
            "X-Hub-Signature-256": "sha256=invalidsignature"
        },
    )

    assert response.status_code == 401


@patch("app.api.routes.review_graph.ainvoke", new_callable=AsyncMock)
@patch("app.api.routes.review_graph.get_state")
def test_approve_review(mock_get_state, mock_ainvoke):
    mock_get_state.return_value = type(
        "Snapshot",
        (),
        {
            "values": {
                "pr_url": "https://github.com/user/project/pull/1"
            },
            "next": ("approval_node",)
        }
    )()

    mock_ainvoke.return_value = {}
    with patch.dict(
        os.environ,
        {"REVIEWER_API_TOKEN": TEST_REVIEWER_TOKEN},
    ):

        response = client.post(
            "/api/reviews/user-project-1/approve",
            json={
                "is_approved": True,
                "reviewer_feedback": ""
            },
            headers={
                "Authorization": f"Bearer {TEST_REVIEWER_TOKEN}"
            },
        )

    assert response.status_code == 200
    assert response.json()["is_approved"] is True
    mock_ainvoke.assert_called_once()


def test_approve_unknown_thread():
    with patch(
        "app.api.routes.review_graph.get_state"
    ) as mock_get_state:

        mock_get_state.return_value = type(
            "Snapshot",
            (),
            {
                "values": {},
                "next": ()
            }
        )()

        with patch.dict(
            os.environ,
            {"REVIEWER_API_TOKEN": TEST_REVIEWER_TOKEN},
        ):
            response = client.post(
                "/api/reviews/unknown-thread/approve",
                json={
                    "is_approved": True,
                    "reviewer_feedback": ""
                },
                headers={
                    "Authorization": f"Bearer {TEST_REVIEWER_TOKEN}"
                },
            )

    assert response.status_code == 404

@patch("app.api.routes.review_graph.ainvoke", new_callable=AsyncMock)
def test_duplicate_webhook_delivery_is_ignored(
    mock_ainvoke, tmp_path, monkeypatch
):
    database_path = tmp_path / "duplicate_test.sqlite"
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(database_path))

    mock_ainvoke.return_value = {
        "__interrupt__": ["waiting for review"]
    }

    payload = {
        "repository": {"full_name": "user/project"},
        "pull_request": {
            "number": 10,
            "html_url": "https://github.com/user/project/pull/10",
        },
    }

    payload_body, signature = create_github_signature(payload)

    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature,
        "X-GitHub-Delivery": "duplicate-test-001",
    }

    first_response = client.post(
        "/api/webhooks/github",
        content=payload_body,
        headers=headers,
    )

    second_response = client.post(
        "/api/webhooks/github",
        content=payload_body,
        headers=headers,
    )

    assert first_response.status_code == 200
    assert first_response.json()["status"] == "waiting_for_review"

    assert second_response.status_code == 200
    assert second_response.json()["status"] == "duplicate"

    mock_ainvoke.assert_called_once()


@patch(
    "app.api.routes.review_graph.ainvoke",
    new_callable=AsyncMock,
    side_effect=[RuntimeError("Temporary workflow failure"), {}],
)
def test_failed_webhook_can_be_retried(
    mock_ainvoke, tmp_path, monkeypatch
):
    database_path = tmp_path / "retry_test.sqlite"
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(database_path))

    payload = {
        "repository": {"full_name": "user/project"},
        "pull_request": {
            "number": 11,
            "html_url": "https://github.com/user/project/pull/11",
        },
    }

    payload_body, signature = create_github_signature(payload)

    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature,
        "X-GitHub-Delivery": "retry-test-001",
    }

    first_response = client.post(
        "/api/webhooks/github",
        content=payload_body,
        headers=headers,
    )

    second_response = client.post(
        "/api/webhooks/github",
        content=payload_body,
        headers=headers,
    )

    assert first_response.status_code == 500
    assert second_response.status_code == 200
    assert second_response.json()["status"] == "waiting_for_review"

    assert mock_ainvoke.call_count == 2


def test_webhook_without_delivery_id_is_rejected():
    payload = {
        "repository": {"full_name": "user/project"},
        "pull_request": {
            "number": 12,
            "html_url": "https://github.com/user/project/pull/12",
        },
    }

    payload_body, signature = create_github_signature(payload)

    response = client.post(
        "/api/webhooks/github",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing GitHub webhook delivery ID."
def test_approve_review_without_token():
    with patch.dict(
        os.environ,
        {"REVIEWER_API_TOKEN": TEST_REVIEWER_TOKEN},
    ):
        response = client.post(
            "/api/reviews/test-thread/approve",
            json={
                "is_approved": True,
                "reviewer_feedback": "",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Missing or invalid reviewer authorization."
    )


def test_approve_review_with_invalid_token():
    with patch.dict(
        os.environ,
        {"REVIEWER_API_TOKEN": TEST_REVIEWER_TOKEN},
    ):
        response = client.post(
            "/api/reviews/test-thread/approve",
            json={
                "is_approved": True,
                "reviewer_feedback": "",
            },
            headers={
                "Authorization": "Bearer wrong-token",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid reviewer token."


def test_approve_review_without_server_configuration():
    with patch.dict(os.environ):
        os.environ.pop("REVIEWER_API_TOKEN", None)

        response = client.post(
            "/api/reviews/test-thread/approve",
            json={
                "is_approved": True,
                "reviewer_feedback": "",
            },
        )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Reviewer authentication is not configured."
    )
def test_webhook_starts_real_graph_and_pauses_for_review(monkeypatch):
    # Use a test webhook secret.
    monkeypatch.setenv("WEBHOOK_SECRET", "integration-test-secret")

    # Mock external operations. No GitHub API or OpenAI calls.
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
            "refactored_code": {"main.py": "print('Hello!')"}
        }

    def mock_apply(state):
        raise AssertionError(
            "Changes must not be applied before reviewer approval."
        )

    # Replace the graph nodes before building the test graph.
    monkeypatch.setattr(
        "app.agent.graph.fetch_pr_node", mock_fetch
    )
    monkeypatch.setattr(
        "app.agent.graph.lint_code_node", mock_lint
    )
    monkeypatch.setattr(
        "app.agent.graph.propose_refactor_node", mock_propose
    )
    monkeypatch.setattr(
        "app.agent.graph.apply_changes_node", mock_apply
    )

    # Build a real LangGraph with an in-memory checkpointer.
    test_graph = build_graph(checkpointer=MemorySaver())

    # Make the FastAPI route use our test graph.
    monkeypatch.setattr(
        "app.api.routes.review_graph", test_graph
    )

    # Avoid writing to the webhook delivery database.
    monkeypatch.setattr(
        "app.api.routes.claim_webhook_delivery",
        lambda delivery_id: True,
    )

    payload = {
        "repository": {
            "full_name": "integration-user/integration-project"
        },
        "pull_request": {
            "number": 987,
            "html_url": (
                "https://github.com/integration-user/"
                "integration-project/pull/987"
            ),
        },
    }

    payload_body, signature = create_github_signature(payload)

    response = client.post(
        "/api/webhooks/github",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
            "X-GitHub-Delivery": "integration-test-delivery-987",
        },
    )

    # Verify the API successfully started the workflow.
    assert response.status_code == 200
    assert response.json()["interrupted"] is True

    thread_id = "integration-user/integration-project-987"

    # Verify the actual graph is paused for human review.
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    snapshot = test_graph.get_state(config)

    assert snapshot.next == ("approval_node",)
    assert snapshot.values["code_contents"] == {
        "main.py": "print('hello')"
    }
    assert snapshot.values["refactored_code"] == {
        "main.py": "print('Hello!')"
    }
    assert snapshot.values["is_approved"] is None
def test_rejection_feedback_reaches_real_graph(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "integration-test-secret")
    monkeypatch.setenv("REVIEWER_API_TOKEN", TEST_REVIEWER_TOKEN)

    proposal_count = {"value": 0}

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
        proposal_count["value"] += 1

        return {
            "refactored_code": {
                "main.py": (
                    "print('First proposal')"
                    if proposal_count["value"] == 1
                    else "print('Improved proposal')"
                )
            }
        }

    def mock_apply(state):
        raise AssertionError(
            "Rejected changes must never be applied."
        )

    monkeypatch.setattr("app.agent.graph.fetch_pr_node", mock_fetch)
    monkeypatch.setattr("app.agent.graph.lint_code_node", mock_lint)
    monkeypatch.setattr("app.agent.graph.propose_refactor_node", mock_propose)
    monkeypatch.setattr("app.agent.graph.apply_changes_node", mock_apply)

    test_graph = build_graph(checkpointer=MemorySaver())

    monkeypatch.setattr("app.api.routes.review_graph", test_graph)
    monkeypatch.setattr(
        "app.api.routes.claim_webhook_delivery",
        lambda delivery_id: True,
    )

    payload = {
        "repository": {
            "full_name": "integration-user/rejection-project"
        },
        "pull_request": {
            "number": 100,
            "html_url": (
                "https://github.com/integration-user/"
                "rejection-project/pull/100"
            ),
        },
    }

    payload_body, signature = create_github_signature(payload)

    webhook_response = client.post(
        "/api/webhooks/github",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
            "X-GitHub-Delivery": "rejection-test-delivery-100",
        },
    )

    assert webhook_response.status_code == 200
    assert proposal_count["value"] == 1

    thread_id = "integration-user/rejection-project-100"

    approval_response = client.post(
        f"/api/reviews/{thread_id}/approve",
        json={
            "is_approved": False,
            "reviewer_feedback": "Improve variable naming.",
        },
        headers={
            "Authorization": f"Bearer {TEST_REVIEWER_TOKEN}"
        },
    )

    assert approval_response.status_code == 200
    assert approval_response.json()["is_approved"] is False
    assert approval_response.json()["interrupted"] is True

    snapshot = test_graph.get_state(
        {"configurable": {"thread_id": thread_id}}
    )

    assert proposal_count["value"] == 2
    assert snapshot.next == ("approval_node",)
    assert snapshot.values["reviewer_feedback"] == (
        "Improve variable naming."
    )
    assert snapshot.values["refactored_code"]["main.py"] == (
        "print('Improved proposal')"
    )
    assert snapshot.values["is_approved"] is False

def test_approval_endpoint_applies_changes_after_approval(monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", "integration-test-secret")
    monkeypatch.setenv("REVIEWER_API_TOKEN", TEST_REVIEWER_TOKEN)

    commit_calls = []

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

    def mock_commit(pr_url, refactored_code, expected_head_sha):
        commit_calls.append({
            "pr_url": pr_url,
            "refactored_code": refactored_code,
            "expected_head_sha": expected_head_sha,
        })
        return "test-commit-sha"

    monkeypatch.setattr("app.agent.graph.fetch_pr_node", mock_fetch)
    monkeypatch.setattr("app.agent.graph.lint_code_node", mock_lint)
    monkeypatch.setattr("app.agent.graph.propose_refactor_node", mock_propose)
    monkeypatch.setattr(
        "app.agent.nodes.commit_refactored_files",
        mock_commit,
    )

    test_graph = build_graph(checkpointer=MemorySaver())

    monkeypatch.setattr("app.api.routes.review_graph", test_graph)
    monkeypatch.setattr(
        "app.api.routes.claim_webhook_delivery",
        lambda delivery_id: True,
    )

    payload = {
        "repository": {"full_name": "integration-user/approval-project"},
        "pull_request": {
            "number": 200,
            "html_url": (
                "https://github.com/integration-user/"
                "approval-project/pull/200"
            ),
        },
    }

    payload_body, signature = create_github_signature(payload)

    webhook_response = client.post(
        "/api/webhooks/github",
        content=payload_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
            "X-GitHub-Delivery": "approval-test-delivery-200",
        },
    )

    assert webhook_response.status_code == 200

    thread_id = "integration-user/approval-project-200"

    approval_response = client.post(
        f"/api/reviews/{thread_id}/approve",
        json={
            "is_approved": True,
            "reviewer_feedback": "",
        },
        headers={
            "Authorization": f"Bearer {TEST_REVIEWER_TOKEN}"
        },
    )

    assert approval_response.status_code == 200

    config = {"configurable": {"thread_id": thread_id}}

    # The endpoint must complete the approved workflow.
    assert commit_calls == [{
        "pr_url": payload["pull_request"]["html_url"],
        "refactored_code": {"main.py": "print('Hello!')"},
        "expected_head_sha": "test-head-sha",
    }]

    final_state = test_graph.get_state(config).values

    assert final_state["is_approved"] is True
    assert final_state["history"][-1]["action"] == "apply_changes"
    assert final_state["history"][-1]["commit_sha"] == "test-commit-sha"
