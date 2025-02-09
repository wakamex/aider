"""Integration tests for GitHub functionality."""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from aider.llm import LLM
from aider.github_issues import GITHUB_API_URL, GitHubIssueClient, PersonalityManager


def run_git(args, cwd=None):
    """Run a git command."""
    result = subprocess.run(["git"] + args, capture_output=True, text=True, check=True, cwd=cwd)
    return result.stdout.strip()

@pytest.fixture(scope="session")
def github_token():
    """Get GitHub token from environment."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        pytest.skip("GITHUB_TOKEN not set")
    return token

@pytest.fixture(scope="session")
def github_client(github_token):
    """Create GitHub client."""
    # Load config and check for test_model setting
    config = {}
    conf_path = Path(".aider.conf.yml")
    if conf_path.exists():
        with open(conf_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
            if "github" in config and "test_model" in config["github"]:
                os.environ["AIDER_TEST_MODEL"] = config["github"]["test_model"]

    client = GitHubIssueClient(token=github_token, llm=LLM(), config=config)
    return client

@pytest.fixture
def github_client_with_repo(github_client, repo):
    """Update GitHub client with local repo path."""
    github_client.repo_path = str(repo)
    github_client.personality.load_personality(repo)
    return github_client

@pytest.fixture(scope="session")
def test_repo(github_client):
    """Create a test repository for integration tests."""
    # First, list and delete any existing test repos
    repos = github_client.get_user_repos()

    for repo in repos:
        if repo["name"].startswith("aider-test-"):
            # Delete the repo
            owner = repo["owner"]["login"]
            github_client.delete_repo(owner, repo["name"])

    # Create new test repo with timestamp
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    repo_name = f"aider-test-{timestamp}"
    description = f"Aider GitHub Integration Test Repository (created {timestamp})"

    response = github_client.session.post(
        f"{GITHUB_API_URL}/user/repos",
        json={
            "name": repo_name,
            "description": description,
            "private": False,
            "auto_init": True,
            "homepage": "https://github.com/Aider-AI/aider",
            "has_wiki": True,
            "has_issues": True
        }
    )

    if response.status_code != 201:
        print(f"\nError creating repository: {response.status_code}")
        print(f"Response: {response.json()}")
        response.raise_for_status()

    repo_data = response.json()

    # Give GitHub a moment to fully create the repository
    time.sleep(2)

    return repo_data

@pytest.fixture
def repo(test_repo, github_token, github_client):
    """Clone and set up local repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Clone repo
        clone_url = test_repo["clone_url"].replace("https://", f"https://x-access-token:{github_token}@")
        run_git(["clone", clone_url, tmpdir])

        # Set local git configs to match GitHub user
        github_client.configure_git_user(tmp_path)

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

@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    with patch("requests.Session") as mock:
        mock.return_value.post.return_value.status_code = 201
        mock.return_value.get.return_value.status_code = 200
        mock.return_value.delete.return_value.status_code = 204
        yield mock.return_value

@pytest.fixture
def personality(github_client):
    """Get personality from user's personality repo."""
    owner = github_client.get_current_user()["login"]

    # Try to get personality from remote repo
    response = github_client.session.get(f"{GITHUB_API_URL}/repos/{owner}/personality/contents/README.md")
    if response.status_code == 200:
        import base64
        return base64.b64decode(response.json()["content"]).decode()
    return None


def test_personality_loading(github_client, personality):
    """Test loading personality from remote repo."""
    input_text = "Hello world"

    # Verify personality was loaded
    assert personality is not None

    # Create a personality manager
    manager = PersonalityManager(github_client)
    manager.personality = personality

    # Test applying personality
    output_text = manager.apply_personality(input_text, llm=github_client.llm)
    assert output_text is not None
    assert output_text != input_text

def test_pr_workflow(github_client, test_repo, repo, mock_io, mock_coder):
    """Test complete PR workflow with descriptive content."""
    # Create project structure
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / "docs").mkdir()
    (repo / "personality").mkdir()

    # Load personality from remote
    github_client.personality.load_personality(repo)

    # Add README with project info
    readme = repo / "README.md"
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
    run_git(["add", "README.md"], cwd=repo)
    run_git(["commit", "-m", "Initial commit: Project structure and README"], cwd=repo)

    # Create feature branch
    run_git(["checkout", "-b", "feature/test-integration"], cwd=repo)

    # Add source file
    src_file = repo / "src" / "main.py"
    src_file.write_text("""
    def main():
        print("Hello from Aider!")

    if __name__ == "__main__":
        main()
    """.strip())

    # Commit source file
    run_git(["add", "src/main.py"], cwd=repo)
    run_git(["commit", "-m", "Add main application file"], cwd=repo)

    # Push changes
    run_git(["push", "-u", "origin", "feature/test-integration"], cwd=repo)

    # Create PR with personality
    pr_data = github_client.create_pull_request(
        owner=test_repo["owner"]["login"],
        repo=test_repo["name"],
        title="Add GitHub Integration Test",
        body="Purpose: This PR demonstrates Aider's GitHub integration features.\nChanges: Project structure setup, basic application code, documentation.\nTesting: This PR is part of Aider's automated integration tests.",
        head="feature/test-integration",
        base="main",
    )

    # Add progress comment with personality
    github_client.create_issue_comment(
        owner=test_repo["owner"]["login"],
        repo=test_repo["name"],
        issue_number=pr_data["number"],
        body="Automated Test Progress\n\n```\nStarting integration test sequence:\n1. Repository created\n2. Files added\n3. PR created\n4. Running file updates...\n```",
    )

    # Update PR progress with personality
    github_client.update_pr_progress(
        owner=test_repo["owner"]["login"],
        repo=test_repo["name"],
        pr_number=pr_data["number"],
        changes=[
            "Completed documentation and test structure",
            "Added tests/test_github_integration.py",
            "Modified TASK.md with requirements",
            "Updated aider/commands.py and github_issues.py",
        ]
    )

    print(f"\nInspect the test results at: {pr_data['html_url']}")
    print(f"Repository: {test_repo['html_url']}")
    print(f"Pull Request: {pr_data['html_url']}")

def test_automation_flow(github_client_with_repo, test_repo, repo):
    """Test the complete automation flow."""
    # Create a test issue with a problem definition
    issue_title = "Add logging configuration"
    issue_body = """Problem: Add logging configuration to the project

    Requirements:
    1. Add a logging.conf file
    2. Configure file and console handlers
    3. Set default level to INFO
    4. Add rotation for file handler

    Please implement this using the Python logging module."""

    issue = github_client_with_repo.create_issue(
        test_repo["owner"]["login"],
        test_repo["name"],
        issue_title,
        issue_body,
        labels=["aider"]
    )

    # Create a temporary directory for the automation run
    with tempfile.TemporaryDirectory() as work_dir:
        work_dir = Path(work_dir)

        # Import here to avoid circular imports
        from aider.github_automation import process_issue_real
        from aider.io import InputOutput
        from aider.coders import Coder
        from aider import models

        # Get model from env var
        model = os.getenv("AIDER_TEST_MODEL", "gemini/gemini-2.0-flash-exp")

        # Process the issue directly
        results = process_issue_real(
            test_repo["owner"]["login"],
            test_repo["name"],
            issue["number"],
            work_dir=work_dir,
            model_name=model,
            verbose=False,
            with_comments=True,
            no_git=False,
            github_client=github_client_with_repo
        )

        # Verify automation directory structure
        issue_dir = work_dir / f"{test_repo['owner']['login']}-{test_repo['name']}-{issue['number']}"
        assert issue_dir.exists(), "Issue directory not created"

        repo_dir = issue_dir / "repo"
        assert repo_dir.exists(), "Repository directory not created"
        assert (repo_dir / ".git").exists(), "Git directory not created"

        # Verify results file
        results_file = issue_dir / ".aider.results.json"
        assert results_file.exists(), "Results file not created"

        # Verify PR creation
        prs = github_client_with_repo.get_repo_prs(
            test_repo["owner"]["login"],
            test_repo["name"]
        )
        assert len(prs) > 0, "No PRs created"

        latest_pr = prs[0]
        assert "Add logging configuration" in latest_pr["title"]

        # Verify PR content
        pr_files = github_client_with_repo.get_pr_files(
            test_repo["owner"]["login"],
            test_repo["name"],
            latest_pr["number"]
        )

        # Should have created logging.conf
        logging_conf_file = next(
            (f for f in pr_files if f["filename"].endswith("logging.conf")),
            None
        )
        assert logging_conf_file is not None, "logging.conf not created"

        # PR should reference the issue
        assert f"fixes #{issue['number']}" in latest_pr["body"].lower()
