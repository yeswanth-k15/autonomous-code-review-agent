from app.agent.state import ReviewState
from app.services.github_commit_service import commit_refactored_files
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.agent.prompts import (
    REFACTOR_SYSTEM_PROMPT,
    build_refactor_prompt,
)
from app.services.github_service import fetch_pull_request_data
from app.tools.linter_tool import run_linter_tool

load_dotenv()


def fetch_pr_node(state: ReviewState) -> dict:
    """Fetch pull request files and record the source commit SHA."""

    code_contents, head_sha = fetch_pull_request_data(
        state["pr_url"]
    )

    if not code_contents:
        raise ValueError(
            "No eligible Python files found in the pull request."
        )

    return {
        "code_contents": code_contents,
        "head_sha": head_sha,
        "history": state.get("history", []) + [
            {
                "action": "fetch_pr",
                "status": "success",
            }
        ],
    }

def lint_code_node(state: dict) -> dict:
    code_contents = state.get("code_contents", {})
    lint_errors = {}

    for filename, code in code_contents.items():
        result = run_linter_tool.invoke(
            {"code_string": code}
        )
        lint_errors[filename] = result

    history = state.get("history", [])

    return {
        "lint_errors": lint_errors,
        "history": history + [
            {"action": "lint_code", "status": "success"}
        ],
    }


def propose_refactor_node(state: dict) -> dict:
    code_contents = state.get("code_contents", {})
    lint_errors = state.get("lint_errors", {})
    reviewer_feedback = state.get("reviewer_feedback", "")

    if not code_contents:
        raise ValueError("No Python code available to refactor.")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

    refactored_code = {}

    for filename, original_code in code_contents.items():
        prompt = build_refactor_prompt(
            filename=filename,
            original_code=original_code,
            lint_errors=lint_errors.get(
                filename,
                "No linting results available."
            ),
            reviewer_feedback=reviewer_feedback,
        )

        response = llm.invoke([
            SystemMessage(content=REFACTOR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ])

        if not isinstance(response.content, str):
            raise TypeError(
                f"Unexpected LLM response for {filename}"
            )

        improved_code = response.content.strip()

        # Remove Markdown code fences if the model includes them.
        if improved_code.startswith("```"):
            lines = improved_code.splitlines()

            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]

            improved_code = "\n".join(lines).strip()

        if not improved_code:
            raise ValueError(
                f"The AI returned empty code for {filename}"
            )

        refactored_code[filename] = improved_code

    history = state.get("history", [])

    return {
        "refactored_code": refactored_code,
        "history": history + [
            {"action": "propose_refactor", "status": "success"}
        ],
    }

def apply_changes_node(state: dict) -> dict:
    """
    Commit refactored files only after explicit reviewer approval.
    """

    is_approved = state.get("is_approved")

    if is_approved is not True:
        history = state.get("history", [])

        return {
            "history": history + [
                {
                    "action": "apply_changes",
                    "status": "skipped",
                }
            ]
        }

    pr_url = state["pr_url"]
    refactored_code = state.get("refactored_code", {})

    if not refactored_code:
        raise ValueError("No refactored code available to commit.")

    commit_sha = commit_refactored_files(
        pr_url=state["pr_url"],
        refactored_code=refactored_code,
        expected_head_sha=state["head_sha"],
    )

    history = state.get("history", [])

    return {
        "history": history + [
            {
                "action": "apply_changes",
                "status": "success",
                "commit_sha": commit_sha,
            }
        ]
    }
