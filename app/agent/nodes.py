
from app.services.github_service import fetch_pull_request_files
from app.tools.linter_tool import run_linter_tool


def fetch_pr_node(state: dict) -> dict:
    """
    Fetch modified Python files from GitHub.
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


def lint_code_node(state: dict) -> dict:
    """
    Analyze all retrieved Python files.
    """

    code_contents = state.get("code_contents", {})

    lint_errors = {}

    for filename, code in code_contents.items():

        result = run_linter_tool.invoke({
            "code_string": code
        })

        lint_errors[filename] = result

    history = state.get("history", [])

    return {
        "lint_errors": lint_errors,
        "history": history + [
            {
                "action": "lint_code",
                "status": "success"
            }
        ]
    }
