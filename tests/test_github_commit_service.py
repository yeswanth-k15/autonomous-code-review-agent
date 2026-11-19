from unittest.mock import MagicMock, patch

from app.services.github_commit_service import commit_refactored_files

import pytest

from app.services.github_commit_service import validate_python_file_path


def test_valid_python_file_path():
    validate_python_file_path("app/main.py")


@pytest.mark.parametrize(
    "filename",
    [
        "../secret.py",
        "app/../../secret.py",
        "/absolute/path.py",
        "app\\main.py",
        "main.txt",
        "",
    ],
)
def test_invalid_python_file_paths(filename):
    with pytest.raises(ValueError):
        validate_python_file_path(filename)
@patch("app.services.github_commit_service.Github")
def test_commit_uses_pull_request_source_repository(mock_github):
    # Mock GitHub client and repositories
    github_client = MagicMock()
    mock_github.return_value = github_client

    base_repository = MagicMock()
    source_repository = MagicMock()

    github_client.get_repo.side_effect = [
        base_repository,
        source_repository,
    ]

    # Mock pull request from a fork
    pull_request = MagicMock()
    base_repository.get_pull.return_value = pull_request
    pull_request.head.sha = "parent-commit-sha"
    pull_request.head.repo.full_name = "contributor/project-fork"
    pull_request.head.ref = "feature-branch"

    # Mock latest source branch commit
    latest_commit = MagicMock()
    latest_commit.commit.sha = "parent-commit-sha"
    latest_commit.commit.commit.tree.sha = "tree-sha"
    latest_commit.commit.commit.sha = "parent-commit-sha"

    source_repository.get_branch.return_value = latest_commit

    # Mock GitHub Git API operations
    blob = MagicMock()
    blob.sha = "blob-sha"
    source_repository.create_git_blob.return_value = blob

    new_tree = MagicMock()
    source_repository.create_git_tree.return_value = new_tree

    new_commit = MagicMock()
    new_commit.sha = "new-commit-sha"
    source_repository.create_git_commit.return_value = new_commit

    git_ref = MagicMock()
    source_repository.get_git_ref.return_value = git_ref

    # Execute
    result = commit_refactored_files(
        pr_url="https://github.com/original/project/pull/10",
        refactored_code={
            "app/main.py": "print('Hello')\n"
        },
        expected_head_sha="parent-commit-sha",
    )

    # Verify
    assert result == "new-commit-sha"

    github_client.get_repo.assert_any_call("original/project")
    github_client.get_repo.assert_any_call("contributor/project-fork")

    source_repository.get_branch.assert_called_once_with(
        "feature-branch"
    )

    source_repository.create_git_blob.assert_called_once()
    source_repository.create_git_tree.assert_called_once()
    source_repository.create_git_commit.assert_called_once()

    git_ref.edit.assert_called_once_with(
        "new-commit-sha",
        force=False
    )

    github_client.close.assert_called_once()
@patch("app.services.github_commit_service.Github")
@patch("app.services.github_commit_service.os.getenv")
def test_failed_commit_does_not_update_branch(mock_getenv, mock_github):
    mock_getenv.return_value = "test-token"

    github_client = MagicMock()
    mock_github.return_value = github_client

    base_repository = MagicMock()
    source_repository = MagicMock()

    github_client.get_repo.side_effect = [
        base_repository,
        source_repository,
    ]

    pull_request = MagicMock()
    base_repository.get_pull.return_value = pull_request

    pull_request.head.sha = "parent-commit-sha"
    pull_request.head.repo.full_name = "contributor/project-fork"
    pull_request.head.ref = "feature-branch"

    latest_commit = MagicMock()
    latest_commit.commit.sha = "parent-commit-sha"
    latest_commit.commit.commit.tree.sha = "tree-sha"
    latest_commit.commit.commit.sha = "parent-commit-sha"

    source_repository.get_branch.return_value = latest_commit

    blob = MagicMock()
    blob.sha = "blob-sha"
    source_repository.create_git_blob.return_value = blob

    # Simulate failure while creating the Git tree.
    source_repository.create_git_tree.side_effect = RuntimeError(
        "GitHub API failure"
    )

    with pytest.raises(RuntimeError, match="GitHub API failure"):
        commit_refactored_files(
            pr_url="https://github.com/original/project/pull/10",
            expected_head_sha="parent-commit-sha",
            refactored_code={
                "app/main.py": "print('Hello')\n"
            },
        )

    # The branch must not be updated after the failure.
    source_repository.get_git_ref.assert_not_called()
    github_client.close.assert_called_once()