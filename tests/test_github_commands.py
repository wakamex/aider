"""Tests for GitHub issue integration."""

import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml

from aider.commands import Commands
from aider.github_issues import GitHubIssueClient, DEFAULT_CONFIG

# Test data
MOCK_ISSUE = {
    "number": 123,
    "title": "Test Issue",
    "body": "This is a test issue",
    "html_url": "https://github.com/owner/repo/issues/123",
}

MOCK_ISSUES = [
    MOCK_ISSUE,
    {
        "number": 124,
        "title": "Another Issue",
        "body": "This is another test issue",
        "html_url": "https://github.com/owner/repo/issues/124",
    }
]

MOCK_CONFIG = {
    "github": {
        "token": "config_token",
        "rate_limit": {
            "max_per_page": 50,
            "default_per_page": 20,
        }
    }
}

@pytest.fixture
def mock_io():
    """Mock IO for testing."""
    mock = MagicMock()
    mock.prompt.return_value = "y"
    return mock

@pytest.fixture
def mock_coder(mock_io):
    """Mock coder for testing."""
    mock = MagicMock()
    mock.io = mock_io
    return mock

@pytest.fixture
def mock_github_client():
    """Mock GitHub client for testing."""
    with patch("aider.github_issues.GitHubIssueClient") as mock:
        client = MagicMock()
        mock.return_value = client
        client.get_repo_issues.return_value = MOCK_ISSUES
        client.get_issue_comments.return_value = []
        client.parse_repo_url.return_value = ("owner", "repo")
        yield client

@pytest.fixture
def commands(mock_io, mock_coder, mock_github_client):
    """Commands instance for testing."""
    with patch("aider.commands.GitHubIssueClient", return_value=mock_github_client):
        cmds = Commands(mock_io, mock_coder)
        cmds.github_client = mock_github_client
        yield cmds

def test_github_client_init():
    """Test GitHub client initialization."""
    # Test with token provided
    client = GitHubIssueClient(token="test_token")
    assert client.token == "test_token"
    assert client.config == DEFAULT_CONFIG
    
    # Test with environment variable
    with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
        client = GitHubIssueClient()
        assert client.token == "env_token"
    
    # Test with config provided
    client = GitHubIssueClient(token="test_token", config={"rate_limit": {"max_per_page": 50}})
    assert client.config["rate_limit"]["max_per_page"] == 50
    assert client.config["rate_limit"]["default_per_page"] == DEFAULT_CONFIG["rate_limit"]["default_per_page"]
    
    # Test without token
    with pytest.raises(ValueError) as exc:
        GitHubIssueClient()
    assert "GitHub token not found" in str(exc.value)

def test_github_client_config_file():
    """Test GitHub client configuration from file."""
    mock_file = mock_open(read_data=yaml.dump(MOCK_CONFIG))
    
    with patch("pathlib.Path.exists") as mock_exists:
        with patch("builtins.open", mock_file):
            mock_exists.return_value = True
            
            # Test loading config from file
            with patch.dict(os.environ, clear=True):  # Clear env vars
                client = GitHubIssueClient()
                assert client.token == "config_token"
                assert client.config["rate_limit"]["max_per_page"] == 50
                assert client.config["rate_limit"]["default_per_page"] == 20
            
            # Test token precedence (direct > env > config)
            client = GitHubIssueClient(token="direct_token")
            assert client.token == "direct_token"
            
            with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}):
                client = GitHubIssueClient()
                assert client.token == "env_token"

def test_github_rate_limit(mock_github_client):
    """Test rate limit handling."""
    mock_github_client.get_rate_limit.return_value = {
        "resources": {
            "core": {
                "limit": 5000,
                "remaining": 4999,
                "reset": 1644141760
            }
        }
    }
    
    rate_limit = mock_github_client.get_rate_limit()
    assert rate_limit["resources"]["core"]["limit"] == 5000

def test_github_commands_init(mock_io, mock_coder):
    """Test GitHub commands initialization."""
    cmds = Commands(mock_io, mock_coder)
    assert cmds.io == mock_io
    assert cmds.coder == mock_coder

def test_ensure_client(commands):
    """Test client initialization in commands."""
    assert commands.ensure_client() is not None

def test_process_issue(commands, mock_github_client):
    """Test processing a single issue."""
    commands.process_issue("owner", "repo", 123)
    mock_github_client.get_issue_comments.assert_called_once_with(
        "owner", "repo", 123
    )

def test_process_issue_no_comments(commands, mock_github_client):
    """Test processing an issue without comments."""
    mock_github_client.get_issue_comments.return_value = []
    commands.process_issue("owner", "repo", 123)

def test_process_repo_issue(commands):
    """Test processing an issue from repo URL."""
    commands.process_repo_issue(
        "https://github.com/owner/repo",
        123
    )

def test_cmd_issue_no_args(commands):
    """Test /issue command with no arguments."""
    result = commands.cmd_issue("")
    assert "Usage:" in result

def test_cmd_issue_url_format(commands):
    """Test /issue command with URL format."""
    result = commands.cmd_issue(
        "https://github.com/owner/repo/issues/123"
    )
    assert result is None

def test_cmd_issue_invalid_url(commands):
    """Test /issue command with invalid URL."""
    result = commands.cmd_issue("invalid_url")
    assert "Invalid issue reference" in result

def test_cmd_issue_shorthand_format(commands):
    """Test /issue command with owner/repo#number format."""
    result = commands.cmd_issue("owner/repo#123")
    assert result is None

def test_cmd_issue_invalid_shorthand(commands):
    """Test /issue command with invalid shorthand."""
    result = commands.cmd_issue("invalid/format")
    assert "Invalid issue reference" in result

def test_cmd_issues_no_args(commands):
    """Test /issues command with no arguments."""
    result = commands.cmd_issues("")
    assert "Usage:" in result

def test_cmd_issues_url_format(commands, mock_github_client):
    """Test /issues command with URL format."""
    result = commands.cmd_issues(
        "https://github.com/owner/repo"
    )
    assert result is None
    mock_github_client.get_repo_issues.assert_called_once()

def test_cmd_issues_shorthand_format(commands, mock_github_client):
    """Test /issues command with owner/repo format."""
    result = commands.cmd_issues("owner/repo")
    assert result is None
    mock_github_client.get_repo_issues.assert_called_once()

def test_cmd_issues_with_results(commands, mock_github_client):
    """Test /issues command with mock results."""
    mock_github_client.get_repo_issues.return_value = MOCK_ISSUES
    result = commands.cmd_issues("owner/repo")
    assert result is None
