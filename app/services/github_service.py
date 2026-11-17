
import os
import re

from dotenv import load_dotenv
from github import Github

load_dotenv()


def fetch_pull_request_files(pr_url: str) -> dict[str, str]:
    """
    Fetch modified Python files from a GitHub Pull Request.

    Returns:
        Dictionary containing filename and source code.
    """

    github_token = os.getenv("GITHUB_TOKEN")

    if not github_token:
        raise ValueError("GITHUB_TOKEN is missing from .env")

    # Validate and extract GitHub PR information
    pattern = (
        r"^https://github\.com/"
        r"([^/]+)/([^/]+)/pull/(\d+)/?$"
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

        code_contents = {}

        # Retrieve modified files
        for file in pull_request.get_files():

            # Only analyze Python files
            if not file.filename.endswith(".py"):
                continue

            # Skip deleted files
            if file.status == "removed":
                continue

            # Retrieve contents from the PR's latest commit
            content = repository.get_contents(
                file.filename,
                ref=pull_request.head.sha
            )

            if isinstance(content, list):
                continue

            code = content.decoded_content.decode("utf-8")

            code_contents[file.filename] = code

        return code_contents

    finally:
        github_client.close()
