"""Integration tests for GitHub functionality."""

import os
import pytest
import time
from pathlib import Path
import tempfile
import subprocess
from unittest.mock import patch

from aider.commands import Commands
from aider.github_issues import GitHubIssueClient

def run_git(args, cwd=None):
    """Run a git command."""
    result = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        check=True,
        cwd=cwd
    )
    return result.stdout.strip()

@pytest.fixture
def github_token():
    """Get GitHub token from environment."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN not set")
    return token

@pytest.fixture
def github_client(github_token):
    """Create GitHub client."""
    return GitHubIssueClient(token=github_token)

@pytest.fixture
def test_repo(github_client):
    """Create a test repository."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    repo_name = f"aider-test-{timestamp}"
    description = f"Aider GitHub Integration Test Repository (created {timestamp})"

    api_url = "https://api.github.com/user/repos"
    response = github_client.session.post(api_url, json={
        "name": repo_name,
        "description": description,
        "private": False,
        "auto_init": True,
        "homepage": "https://github.com/Aider-AI/aider",
        "has_wiki": True,
        "has_issues": True
    })

    if response.status_code != 201:
        print(f"\nError creating repository: {response.status_code}")
        print(f"Response: {response.json()}")
        response.raise_for_status()

    repo_data = response.json()

    # Give GitHub a moment to fully create the repository
    time.sleep(2)

    return repo_data

@pytest.fixture
def local_repo(test_repo, github_token, github_client):
    """Clone and set up local repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Clone repo
        clone_url = test_repo["clone_url"].replace("https://", f"https://x-access-token:{github_token}@")
        run_git(["clone", clone_url, tmpdir])

        # Set local git configs to match GitHub user
        owner = github_client.get_current_user()["login"]
        run_git(["config", "user.name", owner], cwd=tmp_path)
        run_git(["config", "user.email", f"{owner}@users.noreply.github.com"], cwd=tmp_path)

        yield tmp_path

@pytest.fixture
def mock_io():
    """Mock IO for commands."""
    class MockIO:
        def tool_error(self, *args, **kwargs):
            pass
        def tool_output(self, *args, **kwargs):
            pass
    return MockIO()

@pytest.fixture
def mock_coder():
    """Mock coder for commands."""
    class MockCoder:
        def __init__(self):
            self.repo_root = None
    return MockCoder()

def test_pr_workflow(github_client, test_repo, local_repo, mock_io, mock_coder):
    """Test complete PR workflow with descriptive content."""
    # Create project structure
    (local_repo / "src").mkdir()
    (local_repo / "tests").mkdir()
    (local_repo / "docs").mkdir()

    # Add README with project info
    readme = local_repo / "README.md"
    readme.write_text("""
    # Test Project

    This repository demonstrates Aider's GitHub integration features.
    Each commit and PR will show different aspects of the integration.

    ## Features Being Tested
    - PR Creation
    - PR Comments
    - Progress Updates
    - File Change Tracking
    """.strip())

    # Initial commit
    run_git(["add", "README.md"], cwd=local_repo)
    run_git(["commit", "-m", "Initial commit: Project structure and README"], cwd=local_repo)

    # Create feature branch
    run_git(["checkout", "-b", "feature/test-integration"], cwd=local_repo)

    # Add source file
    src_file = local_repo / "src" / "main.py"
    src_file.write_text("""
    def main():
        print("Hello from Aider!")

    if __name__ == "__main__":
        main()
    """.strip())

    run_git(["add", "src/main.py"], cwd=local_repo)
    run_git(["commit", "-m", "Add main application file"], cwd=local_repo)

    # Initialize commands
    commands = Commands(mock_io, mock_coder)
    commands.github_client = github_client
    commands.github_client.repo_path = local_repo  # Set the repo path for git commands

    # Push changes to remote
    run_git(["push", "-u", "origin", "feature/test-integration"], cwd=local_repo)

    # Create detailed PR
    repo_data = test_repo  # Use the repo data from the fixture
    owner = github_client.get_current_user()["login"]
    pr_body = "Purpose: This PR demonstrates Aider's GitHub integration features. Changes: Project structure setup, basic application code, documentation. Testing: This PR is part of Aider's automated integration tests."

    result = commands.cmd_pr(
        f'{owner}/{repo_data["name"]} --title "Add GitHub Integration Test" --body "{pr_body}"'
    )
    assert "Created PR:" in result
    pr_url = result.split(": ")[1]
    pr_number = int(pr_url.split("/")[-1])

    # Add informative comment
    comment_text = """
    Automated Test Progress

    Starting integration test sequence:
    1. Repository created
    2. Files added
    3. PR created
    4. Running file updates...
    """.strip()

    result = commands.cmd_prcomment(
        f"{owner}/{repo_data['name']}#{pr_number} {comment_text}"
    )
    assert result == "Comment added to PR"

    # Add test file
    test_file = local_repo / "tests" / "test_main.py"
    test_file.write_text("""
    def test_main():
        # TODO: Add actual tests
        pass
    """.strip())

    run_git(["add", "tests/test_main.py"], cwd=local_repo)
    run_git(["commit", "-m", "Add test skeleton"], cwd=local_repo)

    # Update progress with details
    result = commands.cmd_prupdate(
        f"{owner}/{repo_data['name']}#{pr_number} Added test framework and skeleton tests"
    )
    assert result == "PR progress updated"

    # Add documentation
    docs_file = local_repo / "docs" / "setup.md"
    docs_file.write_text("""
    # Setup Guide

    1. Clone the repository
    2. Run `python src/main.py`
    """.strip())

    run_git(["add", "docs/setup.md"], cwd=local_repo)
    run_git(["commit", "-m", "Add setup documentation"], cwd=local_repo)

    # Final progress update
    result = commands.cmd_prupdate(
        f"{owner}/{repo_data['name']}#{pr_number} Completed documentation and test structure"
    )
    assert result == "PR progress updated"

    # Print repo URL for inspection
    repo_url = f"https://github.com/{owner}/{repo_data['name']}"
    print(f"\nInspect the test results at: {repo_url}")
    print(f"Repository: {repo_url}")
    print(f"Pull Request: {pr_url}")
