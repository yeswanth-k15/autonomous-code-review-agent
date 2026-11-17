
from app.services.github_service import fetch_pull_request_files


def fetch_pr_node(state: dict) -> dict:
    """
    LangGraph node that fetches modified PR files.
    """

    pr_url = state["pr_url"]

    code_contents = fetch_pull_request_files(pr_url)

    history = state.get("history", [])

    return {
        "code_contents": code_contents,
        "history": history + [
            {
                "action": "fetch_pr",
                "status": "success"
            }
        ]
    }
