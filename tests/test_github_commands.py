"""Tests for GitHub commands."""

from unittest.mock import Mock, patch
import pytest
from aider.github_commands import GitHubCommands

# Test data
MOCK_ISSUE = {
    "number": 123,
    "title": "Test issue",
    "body": "Test description",
    "html_url": "https://github.com/owner/repo/issues/123",
    "labels": []
}

MOCK_COMMENTS = [
    {"body": "Test comment"}
]

@pytest.fixture
def mock_io():
    """Create mock IO interface."""
    return Mock()

@pytest.fixture
def mock_coder():
    """Create mock coder instance."""
    return Mock()

@pytest.fixture
def github_commands(mock_io, mock_coder):
    """Create GitHubCommands instance with mocks."""
    return GitHubCommands(mock_io, mock_coder)

def test_ensure_client(github_commands):
    """Test client initialization."""
    with patch("aider.github_commands.GitHubIssueClient") as mock_client:
        github_commands._ensure_client()
        mock_client.assert_called_once()
        assert github_commands.client is not None

        # Second call shouldn't create new client
        github_commands._ensure_client()
        mock_client.assert_called_once()

def test_process_issue(github_commands):
    """Test processing a single issue."""
    with patch("aider.github_commands.GitHubIssueClient") as mock_client_class:
        # Setup mock client
        mock_client = mock_client_class.return_value
        mock_client.get_repo_issues.return_value = [MOCK_ISSUE]
        mock_client.get_issue_comments.return_value = MOCK_COMMENTS

        # Process issue
        github_commands.process_issue("owner", "repo", 123)

        # Verify API calls
        mock_client.get_repo_issues.assert_called_once()
        mock_client.get_issue_comments.assert_called_once()

        # Verify coder updates
        assert github_commands.coder.set_task.called
        assert github_commands.coder.add_context.called

def test_process_issue_no_comments(github_commands):
    """Test processing issue without comments."""
    with patch("aider.github_commands.GitHubIssueClient") as mock_client_class:
        # Setup mock client
        mock_client = mock_client_class.return_value
        mock_client.get_repo_issues.return_value = [MOCK_ISSUE]

        # Process issue
        github_commands.process_issue("owner", "repo", 123, with_comments=False)

        # Verify API calls
        mock_client.get_repo_issues.assert_called_once()
        mock_client.get_issue_comments.assert_not_called()

def test_process_repo_issue(github_commands):
    """Test processing issue with repository URL."""
    with patch("aider.github_commands.GitHubIssueClient") as mock_client_class:
        # Setup mock client
        mock_client = mock_client_class.return_value
        mock_client.parse_repo_url.return_value = ("owner", "repo")
        mock_client.get_repo_issues.return_value = [MOCK_ISSUE]
        mock_client.get_issue_comments.return_value = MOCK_COMMENTS

        # Process issue
        github_commands.process_repo_issue(
            "https://github.com/owner/repo",
            123
        )

        # Verify URL parsing and API calls
        mock_client.parse_repo_url.assert_called_once()
        mock_client.get_repo_issues.assert_called_once()
        mock_client.get_issue_comments.assert_called_once()
