
import os
import re

from dotenv import load_dotenv
from github import Github

load_dotenv()


def fetch_pull_request_data(
    pr_url: str,
) -> tuple[dict[str, str], str]:
    """Fetch Python files and the source commit SHA from a pull request."""

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

        head_repository = pull_request.head.repo

        if head_repository is None:
            raise ValueError(
                "Pull request source repository is unavailable."
            )

        source_repository = github_client.get_repo(
            head_repository.full_name
        )

        head_sha = pull_request.head.sha

        code_contents = {}

        for file in pull_request.get_files():
            if not file.filename.endswith(".py"):
                continue

            if file.status == "removed":
                continue

            if not file.contents_url:
                continue

            content = source_repository.get_contents(
                file.filename,
                ref=head_sha,
            )

            if isinstance(content, list):
                continue

            code = content.decoded_content.decode("utf-8")
            code_contents[file.filename] = code

        return code_contents, head_sha

    finally:
        github_client.close()


def fetch_pull_request_files(pr_url: str) -> dict[str, str]:
    """Fetch Python files from a pull request."""

    code_contents, _ = fetch_pull_request_data(pr_url)

    return code_contents