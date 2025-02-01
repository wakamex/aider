"""Tests for GitHub commands."""

import pytest
from unittest.mock import MagicMock, patch

from aider.commands import Commands
from aider.github_commands import GitHubCommands
from aider.github_issues import GitHubIssueClient

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
    return MagicMock()


@pytest.fixture
def mock_github():
    return MagicMock()


@pytest.fixture
def mock_coder():
    """Create mock coder instance."""
    return MagicMock()


@pytest.fixture
def github_commands(mock_io, mock_coder):
    """Create GitHubCommands instance with mocks."""
    return GitHubCommands(mock_io, mock_coder)


@pytest.fixture
def commands(mock_io, mock_github):
    commands = Commands(mock_io, mock_io)  # Pass mock_io twice - once for input, once for output
    commands.github = mock_github
    return commands


def test_github_commands_init(mock_io, mock_coder):
    """Test GitHubCommands initialization"""
    github_commands = GitHubCommands(mock_io, mock_coder)
    assert github_commands.io == mock_io
    assert github_commands.coder == mock_coder
    assert github_commands.client is None


def test_ensure_client(github_commands):
    """Test client initialization"""
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


# Command Tests
def test_cmd_issue_no_args(commands, mock_io):
    """Test /issue command with no arguments"""
    commands.cmd_issue("")
    mock_io.tool_error.assert_called_once_with("Please provide an issue reference")


def test_cmd_issue_url_format(commands, mock_io, mock_github):
    """Test /issue command with URL format"""
    url = "https://github.com/owner/repo/issues/123"
    commands.cmd_issue(url)
    mock_github.process_repo_issue.assert_called_once_with("https://github.com/owner/repo", 123)


def test_cmd_issue_invalid_url(commands, mock_io):
    """Test /issue command with invalid URL"""
    url = "https://github.com/owner/repo/invalid/123"
    commands.cmd_issue(url)
    mock_io.tool_error.assert_called_once_with("Invalid issue URL format")


def test_cmd_issue_shorthand_format(commands, mock_io, mock_github):
    """Test /issue command with owner/repo#number format"""
    commands.cmd_issue("owner/repo#123")
    mock_github.process_issue.assert_called_once_with("owner", "repo", 123)


def test_cmd_issue_invalid_shorthand(commands, mock_io):
    """Test /issue command with invalid shorthand format"""
    commands.cmd_issue("invalid-format")
    mock_io.tool_error.assert_called_once_with("Invalid issue reference format")


def test_cmd_issues_no_args(commands, mock_io):
    """Test /issues command with no arguments"""
    commands.cmd_issues("")
    mock_io.tool_error.assert_called_once_with("Please provide a repository reference")


def test_cmd_issues_url_format(commands, mock_io, mock_github):
    """Test /issues command with URL format"""
    url = "https://github.com/owner/repo"
    mock_github.client.parse_repo_url.return_value = ("owner", "repo")
    mock_github.client.get_repo_issues.return_value = []

    commands.cmd_issues(url)
    mock_github._ensure_client.assert_called_once()
    mock_github.client.get_repo_issues.assert_called_once_with("owner", "repo", state="open")


def test_cmd_issues_shorthand_format(commands, mock_io, mock_github):
    """Test /issues command with owner/repo format"""
    mock_github.client.get_repo_issues.return_value = []

    commands.cmd_issues("owner/repo")
    mock_github._ensure_client.assert_called_once()
    mock_github.client.get_repo_issues.assert_called_once_with("owner", "repo", state="open")


def test_cmd_issues_with_results(commands, mock_io, mock_github):
    """Test /issues command with mock issues returned"""
    issues = [
        {
            "number": 1,
            "title": "Test Issue",
            "labels": [{"name": "bug"}],
            "html_url": "https://github.com/owner/repo/issues/1"
        }
    ]
    mock_github.client.get_repo_issues.return_value = issues

    commands.cmd_issues("owner/repo")
    mock_io.tool_output.assert_any_call("\nOpen issues in owner/repo:")
    mock_io.tool_output.assert_any_call("#1 Test Issue [bug]\n  https://github.com/owner/repo/issues/1")
