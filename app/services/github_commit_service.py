from pathlib import PurePosixPath
import os
import re

from dotenv import load_dotenv
from github import Github

load_dotenv()


def validate_python_file_path(filename: str) -> None:
    """Validate a relative Python file path before committing."""

    if not filename or "\x00" in filename:
        raise ValueError("Invalid file path.")

    if "\\" in filename:
        raise ValueError("File paths must use forward slashes.")

    path = PurePosixPath(filename)

    if path.is_absolute():
        raise ValueError("Absolute file paths are not allowed.")

    if ".." in path.parts or "." in path.parts:
        raise ValueError("Path traversal is not allowed.")

    if not filename.endswith(".py"):
        raise ValueError(f"Unsupported file type: {filename}")

    if path.name in {"", ".", ".."}:
        raise ValueError("Invalid Python file path.")


def commit_refactored_files(
    pr_url: str,
    refactored_code: dict[str, str],
    expected_head_sha: str,
    commit_message: str = "Apply AI-assisted code refactoring",
) -> str:
    """
    Commit approved refactored Python files to the PR source branch.
    """

    if not refactored_code:
        raise ValueError("No refactored files available to commit.")

    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        raise ValueError("GITHUB_TOKEN is missing from .env")

    pattern = r"^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$"

    match = re.match(pattern, pr_url.strip())

    if not match:
        raise ValueError("Invalid GitHub Pull Request URL")

    owner, repo_name, pr_number = match.groups()

    github_client = Github(github_token)

    try:
        base_repository = github_client.get_repo(
            f"{owner}/{repo_name}"
        )

        pull_request = base_repository.get_pull(int(pr_number))
        # Reject refactoring if the PR changed after code was fetched.
        if pull_request.head.sha != expected_head_sha:
            raise RuntimeError(
                "Pull request has changed since review started. "
                "Please restart the review."
            )

        # Get the repository and branch from which the PR originated.
        head_repository = pull_request.head.repo

        if head_repository is None:
            raise ValueError(
                "Pull request source repository is unavailable."
            )

        source_repository = github_client.get_repo(
            head_repository.full_name
        )

        branch = pull_request.head.ref

        latest_commit = source_repository.get_branch(branch)
        # Ensure the source branch still points to the reviewed commit.
        if latest_commit.commit.sha != expected_head_sha:
            raise RuntimeError(
                "Source branch has changed since review started. "
                "Please restart the review."
            )

        # Get the tree SHA, not the commit SHA.
        base_tree = source_repository.get_git_tree(
            latest_commit.commit.commit.tree.sha
        )

        elements = []

        for filename, code in refactored_code.items():
            validate_python_file_path(filename)

            blob = source_repository.create_git_blob(
                code,
                "utf-8"
            )

            elements.append({
                "path": filename,
                "mode": "100644",
                "type": "blob",
                "sha": blob.sha,
            })

        new_tree = source_repository.create_git_tree(
            elements,
            base_tree
        )

        new_commit = source_repository.create_git_commit(
            commit_message,
            new_tree,
            [latest_commit.commit.commit]
        )

        source_repository.get_git_ref(
            f"heads/{branch}"
        ).edit(
            new_commit.sha,
            force=False
        )

        return new_commit.sha

    finally:
        github_client.close()