
import os
import re

from dotenv import load_dotenv
from github import Github

load_dotenv()


def commit_refactored_files(
    pr_url: str,
    refactored_code: dict[str, str],
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

    pattern = (
        r"^https://github\.com/([^/]+)/([^/]+)/pull/(\d+)/?$"
    )

    match = re.match(pattern, pr_url.strip())

    if not match:
        raise ValueError("Invalid GitHub Pull Request URL")

    owner, repo_name, pr_number = match.groups()

    github_client = Github(github_token)

    try:
        repository = github_client.get_repo(
            f"{owner}/{repo_name}"
        )

        pull_request = repository.get_pull(int(pr_number))

        # Always commit to the source branch of the pull request.
        branch = pull_request.head.ref

        latest_commit = repository.get_branch(branch)
        base_tree = repository.get_git_tree(
            latest_commit.commit.sha
        )

        elements = []

        for filename, code in refactored_code.items():

            if not filename.endswith(".py"):
                raise ValueError(
                    f"Unsupported file type: {filename}"
                )

            blob = repository.create_git_blob(
                code,
                "utf-8"
            )

            elements.append({
                "path": filename,
                "mode": "100644",
                "type": "blob",
                "sha": blob.sha,
            })

        new_tree = repository.create_git_tree(
            elements,
            base_tree
        )

        new_commit = repository.create_git_commit(
            commit_message,
            new_tree,
            [latest_commit.commit.commit]
        )

        repository.get_git_ref(
            f"heads/{branch}"
        ).edit(new_commit.sha)

        return new_commit.sha

    finally:
        github_client.close()
