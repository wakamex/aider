"""Tests for GitHub issue integration."""

import os
import time
from unittest import mock
import pytest
import responses
from aider.github_issues import GitHubIssueClient

# Test data
MOCK_TOKEN = "test-token"
MOCK_OWNER = "test-owner"
MOCK_REPO = "test-repo"
MOCK_ISSUE_NUMBER = 123
BASE_URL = "https://api.github.com"

@pytest.fixture
def github_client():
    """Create a GitHubIssueClient with test token."""
    with mock.patch.dict(os.environ, {"GITHUB_TOKEN": MOCK_TOKEN}):
        return GitHubIssueClient()

@pytest.fixture
def mock_response():
    """Create a mock response with rate limit headers."""
    return {
        "X-RateLimit-Remaining": "4999",
        "X-RateLimit-Reset": str(int(time.time()) + 3600)
    }

def test_client_init_with_token():
    """Test client initialization with explicit token."""
    client = GitHubIssueClient(token=MOCK_TOKEN)
    assert client.token == MOCK_TOKEN
    assert "token" in client.session.headers["Authorization"]

def test_client_init_with_env_var():
    """Test client initialization with environment variable."""
    with mock.patch.dict(os.environ, {"GITHUB_TOKEN": MOCK_TOKEN}):
        client = GitHubIssueClient()
        assert client.token == MOCK_TOKEN

def test_client_init_no_token():
    """Test client initialization with no token raises error."""
    with mock.patch.dict(os.environ, clear=True):
        with pytest.raises(ValueError, match="GitHub token required"):
            GitHubIssueClient()

@pytest.mark.parametrize("url,expected", [
    ("https://github.com/owner/repo", ("owner", "repo")),
    ("http://github.com/owner/repo/", ("owner", "repo")),
    ("https://github.com/owner/repo.git", ("owner", "repo")),
])
def test_parse_repo_url_valid(url, expected):
    """Test parsing valid GitHub repository URLs."""
    assert GitHubIssueClient.parse_repo_url(url) == expected

@pytest.mark.parametrize("url", [
    "https://github.com",
    "https://github.com/owner",
    "not-a-url",
    "https://gitlab.com/owner/repo",
])
def test_parse_repo_url_invalid(url):
    """Test parsing invalid GitHub repository URLs."""
    with pytest.raises(ValueError, match="Invalid GitHub repository URL"):
        GitHubIssueClient.parse_repo_url(url)

@responses.activate
def test_get_repo_issues(github_client, mock_response):
    """Test fetching repository issues."""
    # Mock the API response
    issues_url = f"{BASE_URL}/repos/{MOCK_OWNER}/{MOCK_REPO}/issues"
    mock_issues = [
        {"number": 1, "title": "First issue"},
        {"number": 2, "title": "Second issue"}
    ]
    responses.add(
        responses.GET,
        issues_url,
        json=mock_issues,
        headers=mock_response,
        status=200
    )

    # Make request and verify
    issues = github_client.get_repo_issues(MOCK_OWNER, MOCK_REPO)
    assert len(issues) == 2
    assert issues[0]["number"] == 1
    assert issues[1]["title"] == "Second issue"

@responses.activate
def test_get_issue_comments(github_client, mock_response):
    """Test fetching issue comments."""
    # Mock the API response
    comments_url = f"{BASE_URL}/repos/{MOCK_OWNER}/{MOCK_REPO}/issues/{MOCK_ISSUE_NUMBER}/comments"
    mock_comments = [
        {"id": 1, "body": "First comment"},
        {"id": 2, "body": "Second comment"}
    ]
    responses.add(
        responses.GET,
        comments_url,
        json=mock_comments,
        headers=mock_response,
        status=200
    )

    # Make request and verify
    comments = github_client.get_issue_comments(MOCK_OWNER, MOCK_REPO, MOCK_ISSUE_NUMBER)
    assert len(comments) == 2
    assert comments[0]["id"] == 1
    assert comments[1]["body"] == "Second comment"

@responses.activate
def test_rate_limit_handling(github_client):
    """Test rate limit handling and sleep."""
    # Mock rate limited response
    issues_url = f"{BASE_URL}/repos/{MOCK_OWNER}/{MOCK_REPO}/issues"
    reset_time = int(time.time()) + 2
    responses.add(
        responses.GET,
        issues_url,
        json=[],
        headers={
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_time)
        },
        status=200
    )

    # Mock time.sleep to avoid actual waiting
    with mock.patch("time.sleep") as mock_sleep:
        github_client.get_repo_issues(MOCK_OWNER, MOCK_REPO)
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 0 <= sleep_time <= 2  # Should sleep until reset time

@responses.activate
def test_request_with_params(github_client, mock_response):
    """Test making requests with query parameters."""
    issues_url = f"{BASE_URL}/repos/{MOCK_OWNER}/{MOCK_REPO}/issues"
    responses.add(
        responses.GET,
        issues_url,
        json=[],
        headers=mock_response,
        status=200
    )

    # Make request with parameters
    github_client.get_repo_issues(
        MOCK_OWNER,
        MOCK_REPO,
        state="closed",
        labels=["bug", "high-priority"],
        since="2024-01-01T00:00:00Z"
    )

    # Verify request parameters
    request = responses.calls[0].request
    assert "state=closed" in request.url
    assert "labels=bug,high-priority" in request.url
    assert "since=2024-01-01T00:00:00Z" in request.url
