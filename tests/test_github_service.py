
from unittest.mock import MagicMock, patch

from app.services.github_service import fetch_pull_request_files


@patch("app.services.github_service.Github")
def test_fetch_pull_request_files(mock_github):

    # Mock GitHub client
    mock_client = MagicMock()
    mock_github.return_value = mock_client

    # Mock repository
    mock_repo = MagicMock()
    mock_source_repo = MagicMock()

    mock_client.get_repo.side_effect = [
        mock_repo,
        mock_source_repo,
    ]

    # Mock Pull Request
    mock_pr = MagicMock()
    mock_repo.get_pull.return_value = mock_pr

    mock_pr.head.sha = "test-commit-sha"
    mock_pr.head.repo.full_name = "user/project"

    # Mock modified file
    mock_file = MagicMock()
    mock_file.filename = "main.py"
    mock_file.status = "modified"

    mock_pr.get_files.return_value = [mock_file]

    # Mock file content
    mock_content = MagicMock()
    mock_content.decoded_content = b"print('Hello World')"

    mock_source_repo.get_contents.return_value = mock_content

    with patch.dict("os.environ", {"GITHUB_TOKEN": "test-token"}):

        result = fetch_pull_request_files(
            "https://github.com/user/project/pull/1"
        )

    assert result == {
        "main.py": "print('Hello World')"
    }

    assert mock_client.get_repo.call_count == 2

    mock_client.get_repo.assert_any_call("user/project")

    mock_source_repo.get_contents.assert_called_once_with(
        "main.py",
        ref="test-commit-sha",
    )

    mock_repo.get_pull.assert_called_once_with(1)

    mock_source_repo.get_contents.assert_called_once_with(
        "main.py",
        ref="test-commit-sha",
    )

    mock_client.close.assert_called_once()
