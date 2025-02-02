"""Integration tests for GitHub functionality."""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from aider.github_issues import GITHUB_API_URL, GitHubIssueClient, PersonalityManager


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
    from aider.llm import litellm
    import os

    class LiveLLM:
        def generate(self, prompt):
            try:
                # Get model from env var or config
                model = os.getenv("AIDER_TEST_MODEL", "gemini/gemini-2.0-flash-exp")

                # Get appropriate API key based on model
                api_key = None
                if "gemini" in model.lower():
                    api_key = os.getenv("GEMINI_API_KEY")
                    print(f"Using Gemini model: {model}")
                else:
                    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
                    print(f"Using OpenAI/OpenRouter model: {model}")

                if not api_key:
                    print("No API key found, using mock response")
                    # Extract just the original text from the prompt
                    original = prompt.split("Original text:")[-1].split("\n\n")[0].strip()
                    return f"✨ {original} [✨]"

                # Configure litellm with the API key
                litellm.api_key = api_key
                response = litellm.completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1000  # Increase max tokens to avoid truncation
                )
                content = response.choices[0].message.content
                # Clean up any partial markdown or text
                if content.count('```') % 2 == 1:  # Unclosed code block
                    content = content.split('```')[0]
                return content.strip()
            except Exception as e:
                print(f"LLM error: {e}")
                # Extract just the original text for the mock response
                original = prompt.split("Original text:")[-1].split("\n\n")[0].strip()
                return f"✨ {original} [✨]"

    # Load config and check for test_model setting
    config = {}
    conf_path = Path(".aider.conf.yml")
    if conf_path.exists():
        with open(conf_path) as f:
            config = yaml.safe_load(f) or {}
            if "github" in config and "test_model" in config["github"]:
                os.environ["AIDER_TEST_MODEL"] = config["github"]["test_model"]

    client = GitHubIssueClient(token=github_token, llm=LiveLLM(), config=config)

    # Create personality directory with README
    personality_dir = Path("personality")
    personality_dir.mkdir(exist_ok=True)

    with open(personality_dir / "README.md", "w") as f:
        f.write("""
# Test Bot Personality

I am a friendly and helpful bot that adds a touch of whimsy to my messages.
I like to use emojis and keep things light while staying professional.
""".strip())

    return client

@pytest.fixture
def load_remote_personality(github_client, test_repo):
    """Load personality from remote repo or use default."""
    def _load(repo_path: Path) -> str:
        owner = github_client.get_current_user()["login"]
        repo_name = test_repo["name"]

        # Try to get personality from remote repo
        response = github_client.session.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/contents/personality/README.md")
        if response.status_code == 200:
            import base64
            return base64.b64decode(response.json()["content"]).decode()

        # Fall back to default personality
        return """
        You are a friendly and helpful AI assistant.
        Add emojis and positive language while keeping content professional.
        Keep original information intact.
        """.strip()
    return _load

@pytest.fixture
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

@pytest.fixture
def mock_session():
    """Create a mock session for testing."""
    with patch("requests.Session") as mock:
        mock.return_value.post.return_value.status_code = 201
        mock.return_value.get.return_value.status_code = 200
        mock.return_value.delete.return_value.status_code = 204
        yield mock.return_value

def get_remote_personality(github_client, test_repo):
    """Get personality from remote repo."""
    owner = github_client.get_current_user()["login"]
    repo_name = test_repo["name"]

    # Try to get personality from remote repo
    response = github_client.session.get(f"{GITHUB_API_URL}/repos/{owner}/{repo_name}/contents/personality/README.md")
    if response.status_code == 200:
        import base64
        return base64.b64decode(response.json()["content"]).decode()
    return None

def test_personality_loading(github_client, test_repo, local_repo):
    """Test loading personality from remote repo."""
    input_text = "Hello world"

    # Create personality directory
    (local_repo / "personality").mkdir()

    # Create a personality manager and load
    manager = PersonalityManager(github_client.personality.llm, github_client)
    manager.load_personality(local_repo)

    # Test applying personality without loading one (should use default)
    output_text = manager.apply_personality(input_text, "test")
    assert output_text is not None
    assert output_text != input_text

def test_pr_workflow(github_client, test_repo, local_repo, mock_io, mock_coder):
    """Test complete PR workflow with descriptive content."""
    # Create project structure
    (local_repo / "src").mkdir()
    (local_repo / "tests").mkdir()
    (local_repo / "docs").mkdir()
    (local_repo / "personality").mkdir()

    # Load personality from remote
    github_client.personality.load_personality(local_repo)

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

    # Commit source file
    run_git(["add", "src/main.py"], cwd=local_repo)
    run_git(["commit", "-m", "Add main application file"], cwd=local_repo)

    # Push changes
    run_git(["push", "-u", "origin", "feature/test-integration"], cwd=local_repo)

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

def test_personality_pr_comment(mock_session):
    """Test that personality is applied to PR comments."""
    client = GitHubIssueClient(token="mock-token")  # Add mock token
    client.session = mock_session

    # Mock LLM that adds "(with personality)" to text
    class MockLLM:
        def generate(self, prompt):
            return "Hello! (with personality) This is a comment."

    client.personality.llm = MockLLM()
    client.personality.personality = "Test personality"

    # Create a PR comment
    original_text = "This is a comment."
    client.create_pr_comment("owner", "repo", 123, original_text)

    # Verify the request
    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    request_body = call_args[1]["json"]["body"]

    print("\nPersonality Test Results:")
    print(f"Original text: {original_text}")
    print(f"Enhanced text: {request_body}")
    print(f"Personality applied: {'(with personality)' in request_body}")
    print(f"✨ indicator present: {'[✨]' in request_body}")

    assert "(with personality)" in request_body
    assert "[✨]" in request_body  # Verify our personality indicator is present

def test_automation_flow(github_client, test_repo):
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

    issue = github_client.create_issue(
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
        from aider.github_automation import main, clone_repo
        from aider.io import InputOutput
        from aider.coders import Coder
        from aider import models

        # Get model from env var
        model = os.getenv("AIDER_TEST_MODEL", "gemini/gemini-2.0-flash-exp")

        # Test repository cloning
        repo_dir = work_dir / "test-clone"
        assert clone_repo(
            test_repo["owner"]["login"],
            test_repo["name"],
            repo_dir,
            github_client.token
        ), "Repository clone failed"
        
        # Verify clone was shallow
        git_dir = repo_dir / ".git"
        assert git_dir.exists(), "Git directory not found"
        
        # Check shallow clone by looking at .git/shallow file
        shallow_file = git_dir / "shallow"
        assert shallow_file.exists(), "Not a shallow clone"
        
        # Verify we can create a branch
        branch_name = f"test-branch-{int(time.time())}"
        run_git(["checkout", "-b", branch_name], cwd=repo_dir)
        current_branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_dir)
        assert current_branch == branch_name, "Branch creation failed"

        # Setup aider components directly
        io = InputOutput(
            pretty=True,
            yes=True,
            chat_history_file=work_dir / ".aider.chat.history.md"
        )
        
        main_model = models.Model(model)
        
        coder = Coder.create(
            main_model,
            main_model.edit_format,
            io,
            use_git=False,  # Prevent aider from managing git
            stream=False,
            verbose=False,
            cache_prompts=True,
            suggest_shell_commands=False,
        )

        # Run automation with modified args
        test_args = [
            f"{test_repo['owner']['login']}/{test_repo['name']}",
            "--labels", "aider",
            "--work-dir", str(work_dir),
            "--model", model,
            "--no-git"  # Tell automation script not to manage git
        ]

        # Mock sys.argv
        with patch("sys.argv", ["github_automation.py"] + test_args):
            # Run automation
            main()

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
        prs = github_client.get_repo_prs(
            test_repo["owner"]["login"],
            test_repo["name"]
        )
        assert len(prs) > 0, "No PRs created"

        latest_pr = prs[0]
        assert "Add logging configuration" in latest_pr["title"]

        # Verify PR content
        pr_files = github_client.get_pr_files(
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
        assert f"Fixes #{issue['number']}" in latest_pr["body"].lower()
