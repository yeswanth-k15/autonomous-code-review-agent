
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@patch("app.api.routes.review_graph.ainvoke", new_callable=AsyncMock)
def test_github_webhook(mock_ainvoke):
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

    response = client.post(
        "/api/webhooks/github",
        json=payload
    )

    assert response.status_code == 200
    assert response.json()["thread_id"] == "user/project-1"
    assert response.json()["status"] == "waiting_for_review"
    mock_ainvoke.assert_called_once()


def test_github_webhook_without_pull_request():
    response = client.post(
        "/api/webhooks/github",
        json={"action": "opened"}
    )

    assert response.status_code == 400


@patch("app.api.routes.review_graph.ainvoke", new_callable=AsyncMock)
@patch("app.api.routes.review_graph.get_state")
def test_approve_review(mock_get_state, mock_ainvoke):
    mock_get_state.return_value = type(
        "Snapshot",
        (),
        {
            "values": {"pr_url": "https://github.com/user/project/pull/1"},
            "next": ("approval_node",)
        }
    )()

    mock_ainvoke.return_value = {}

    response = client.post(
        "/api/reviews/user-project-1/approve",
        json={
            "is_approved": True,
            "reviewer_feedback": ""
        }
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

        response = client.post(
            "/api/reviews/unknown-thread/approve",
            json={
                "is_approved": True,
                "reviewer_feedback": ""
            }
        )

    assert response.status_code == 404
