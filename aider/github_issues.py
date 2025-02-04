"""GitHub Issue Client for interacting with GitHub's API."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import datetime
import requests
import yaml
import re
import subprocess
import logging

# Constants for GitHub API
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
DEFAULT_CONFIG = {
    "rate_limit": {
        "max_per_page": 100,
        "default_per_page": 30,
    },
    "personality": {
        "enabled": True,
    },
    "test_model": "gpt-3.5-turbo",  # Default model for tests
}

def merge_configs(base: Dict, update: Dict) -> Dict:
    """Deep merge two configs, with update taking precedence."""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result

class PersonalityManager:
    """Manages personality-driven content for GitHub interactions."""

    def __init__(self, llm=None, github_client=None):
        self.llm = llm
        self.personality = None
        self.enabled = True  # Can be toggled via config
        self.github_client = github_client

    def load_personality(self, repo_path: Path):
        """Load personality from user's remote personality repo."""
        if not self.github_client:
            logging.info("No github client available for remote loading")
            return

        try:
            owner = self.github_client.get_current_user()["login"]
            logging.info(f"Trying to load remote personality from {owner}/personality")
            response = self.github_client.session.get(f"{GITHUB_API_URL}/repos/{owner}/personality/contents/README.md")
            if response.status_code == 200:
                import base64
                self.personality = base64.b64decode(response.json()["content"]).decode().strip()
                logging.info(f"Successfully loaded remote personality")
            else:
                logging.info(f"Failed to get remote personality: {response.status_code}")
        except Exception as e:
            logging.info(f"Failed to load remote personality: {e}")

    def apply_personality(self, text: str, context: str = "") -> str:
        """Apply personality to text if enabled and available.

        Args:
            text: Original text content
            context: Type of content (e.g. 'PR comment', 'issue update')

        Returns:
            Text with personality applied, or original text if disabled/error
        """
        logging.info(f"\nDebug: PersonalityManager.apply_personality")
        logging.info(f"Enabled: {self.enabled}")
        logging.info(f"Has personality: {bool(self.personality)}")
        logging.info(f"Has LLM: {bool(self.llm)}")

        if not self.enabled or not self.personality or not self.llm:
            logging.info("Skipping personality - not enabled, no personality loaded, or no LLM")
            return text

        # Remove any existing personality markers
        text = re.sub(r'\s*\[✨\]\s*$', '', text.strip())

        try:
            # Create prompt for LLM
            prompt = f"""
            You are enhancing text with personality.
            Use the personality description below to guide your response:

            {self.personality}

            Original text:
            {text}

            Respond with a SINGLE line of flavor text to be added prior to the original text.
            """

            logging.info(f"\nDebug: Sending prompt to LLM:\n{prompt}")
            response = self.llm.generate(prompt)
            logging.info(f"\nDebug: LLM response:\n{response}")

            response = response.split("\n")[0].strip()
            return response + "\n" + text
        except Exception as e:
            logging.info(f"Error applying personality: {e}")
            return text

class GitHubIssueClient:
    """Client for interacting with GitHub Issues API."""

    def __init__(self, token: Optional[str] = None, config: Optional[Dict] = None, repo_path: Optional[str] = None, llm=None):
        """Initialize the GitHub client.

        Args:
            token: GitHub API token. If not provided, will try to read from GITHUB_TOKEN env var
                  or .aider.conf.yml github.token
            config: Configuration dict. If not provided, will try to read from .aider.conf.yml
            repo_path: Path to the repository
            llm: LLM instance for personality-driven content
        """
        self.config = DEFAULT_CONFIG.copy()
        self.repo_path = repo_path
        self.personality = PersonalityManager(llm, self)

        # Try to load config from .aider.conf.yml
        conf_path = Path(".aider.conf.yml")
        yaml_config = {}
        if conf_path.exists():
            try:
                with open(conf_path) as f:
                    yaml_config = yaml.safe_load(f) or {}
            except Exception:
                pass

        # Load GitHub config section
        github_config = yaml_config.get("github", {})

        # Update personality settings
        personality_config = github_config.get("personality", {})
        self.personality.enabled = personality_config.get("enabled", True)

        if self.repo_path:
            self.personality.load_personality(Path(self.repo_path))

        # Merge configs
        if config:
            self.config = merge_configs(self.config, config)
        if github_config:
            self.config = merge_configs(self.config, github_config)

        # Token precedence: direct > env > config
        self.token = token or os.getenv(GITHUB_TOKEN_ENV)
        if not self.token and yaml_config.get("github", {}).get("token"):
            self.token = yaml_config["github"]["token"]

        if not self.token:
            raise ValueError(
                f"GitHub token not found. Please set {GITHUB_TOKEN_ENV} environment variable "
                "or add github.token to .aider.conf.yml"
            )

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        })

    def get_rate_limit(self) -> Dict:
        """Get current rate limit status.

        Returns:
            Dict containing rate limit information
        """
        response = self.session.get(f"{GITHUB_API_URL}/rate_limit")
        response.raise_for_status()
        return response.json()

    def get_repo_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: Optional[int] = None
    ) -> List[Dict]:
        """Get issues from a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open, closed, all)
            per_page: Number of issues per page (max 100)

        Returns:
            List of issues
        """
        if per_page is None:
            per_page = self.config["rate_limit"]["default_per_page"]
        per_page = min(per_page, self.config["rate_limit"]["max_per_page"])

        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues"
        params = {"state": state, "per_page": per_page}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_issue_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        per_page: Optional[int] = None
    ) -> List[Dict]:
        """Get comments for an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            per_page: Number of comments per page (max 100)

        Returns:
            List of comments
        """
        if per_page is None:
            per_page = self.config["rate_limit"]["default_per_page"]
        per_page = min(per_page, self.config["rate_limit"]["max_per_page"])

        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        params = {"per_page": per_page}

        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def create_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str
    ) -> Dict:
        """Create a comment on an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            body: Comment text

        Returns:
            Created comment data
        """
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        body = self.personality.apply_personality(body, context="issue comment")
        data = {"body": body}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def update_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        state: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict:
        """Update an issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            state: New state (open, closed)
            title: New title
            body: New body text
            labels: New list of label names

        Returns:
            Updated issue data
        """
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{issue_number}"
        data = {}
        if state is not None:
            data["state"] = state
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = self.personality.apply_personality(body, context="issue update")
        if labels is not None:
            data["labels"] = labels

        response = self.session.patch(url, json=data)
        response.raise_for_status()
        return response.json()

    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: Optional[str] = None,
        draft: bool = False
    ) -> Dict:
        """Create a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Branch to merge from
            base: Branch to merge into (default: main)
            body: PR description
            draft: Whether to create as draft PR

        Returns:
            Created PR data
        """
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls"
        if body:
            body = self.personality.apply_personality(body, context="PR description")
        data = {
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft
        }
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def create_pr_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str
    ) -> Dict:
        """Create a comment on a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            body: Comment text

        Returns:
            Created comment data
        """
        # Use issues endpoint since PRs are issues
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        body = self.personality.apply_personality(body, context="PR comment")
        data = {"body": body}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_pr_comments(
        self,
        owner: str,
        repo: str,
        pr_number: int
    ) -> List[Dict]:
        """Get comments on a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number

        Returns:
            List of comments
        """
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_current_branch(self, owner: str, repo: str) -> str:
        """Get the current branch name.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Current branch name
        """
        # Run git command to get current branch
        try:
            if not self.repo_path:
                return "main"  # Fallback if no repo path set

            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            # Fallback to main if we can't get the current branch
            return "main"

    def get_file_changes(self) -> Dict[str, List[str]]:
        """Get file changes in the current branch using git.

        Returns:
            Dict with added, modified, and deleted files
        """
        def run_git(args: List[str]) -> List[str]:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                check=True
            )
            return [line for line in result.stdout.split("\n") if line]

        try:
            # Get files changed compared to base branch
            changed = run_git(["diff", "--name-status", "HEAD^"])

            changes = {
                "added": [],
                "modified": [],
                "deleted": []
            }

            for line in changed:
                status, file = line.split("\t", 1)
                if status.startswith("A"):
                    changes["added"].append(file)
                elif status.startswith("M"):
                    changes["modified"].append(file)
                elif status.startswith("D"):
                    changes["deleted"].append(file)

            return changes

        except subprocess.CalledProcessError:
            return {"added": [], "modified": [], "deleted": []}

    def update_pr_progress(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        changes: List[str],
        include_files: bool = True
    ) -> Dict:
        """Update PR with progress information.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            changes: List of changes made
            include_files: Whether to include file changes

        Returns:
            Created comment data
        """
        # Get existing comments
        comments = self.get_pr_comments(owner, repo, pr_number)

        # Find progress comment if it exists
        progress_header = "## 🔄 Progress Update"
        progress_comment = None
        for comment in comments:
            if comment["body"].startswith(progress_header):
                progress_comment = comment
                break

        # Format changes
        change_list = "\n".join(f"- {change}" for change in changes)
        body = f"{progress_header}\n\n{change_list}\n"

        # Add file changes if requested
        if include_files:
            file_changes = self.get_file_changes()
            if any(file_changes.values()):
                body += "\n### 📁 Files Changed\n"
                if file_changes["added"]:
                    files = "\n".join(f"- Added: `{f}`" for f in file_changes["added"])
                    body += f"\n{files}"
                if file_changes["modified"]:
                    files = "\n".join(f"- Modified: `{f}`" for f in file_changes["modified"])
                    body += f"\n{files}"
                if file_changes["deleted"]:
                    files = "\n".join(f"- Deleted: `{f}`" for f in file_changes["deleted"])
                    body += f"\n{files}"

        # Add timestamp
        timestamp = "Last updated: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body += f"\n\n{timestamp}"

        logging.info(f"\nDebug: Original body before personality:\n{body}")

        # Don't apply personality because it will get added in create_pr_comment
        # body = self.personality.apply_personality(body, context="PR progress update")
        # logging.info(f"\nDebug: Body after personality:\n{body}")

        # Update or create progress comment
        if progress_comment:
            url = progress_comment["url"]
            response = self.session.patch(url, json={"body": body})
            response.raise_for_status()
            return response.json()
        else:
            return self.create_pr_comment(owner, repo, pr_number, body)

    def get_current_user(self) -> Dict:
        """Get the currently authenticated user.

        Returns:
            Dict with user data including 'login' (username)
        """
        url = f"{GITHUB_API_URL}/user"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def configure_git_user(self, repo_dir: str) -> None:
        """Configure git user settings for a repository based on GitHub user.

        Args:
            repo_dir: Path to the git repository
        """
        user = self.get_current_user()
        owner = user["login"]
        subprocess.run(
            ["git", "config", "user.name", owner],
            cwd=repo_dir,
            check=True,
            capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", f"{owner}@users.noreply.github.com"],
            cwd=repo_dir,
            check=True,
            capture_output=True
        )

    def get_user_repos(self) -> List[Dict]:
        """Get list of repositories for the authenticated user."""
        url = f"{GITHUB_API_URL}/user/repos"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def delete_repo(self, owner: str, repo: str) -> None:
        """Delete a repository."""
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
        response = self.session.delete(url)
        response.raise_for_status()

    @staticmethod
    def parse_repo_url(url: str) -> Tuple[str, str]:
        """Parse owner and repo from a GitHub repository URL.

        Args:
            url: GitHub repository URL

        Returns:
            Tuple of (owner, repo)

        Raises:
            ValueError: If URL format is invalid
        """
        # Remove .git suffix if present
        url = url.rstrip(".git")

        # Handle both HTTPS and SSH URLs
        patterns = [
            r"https?://github\.com/([^/]+)/([^/]+)",  # HTTPS
            r"git@github\.com:([^/]+)/([^/]+)",       # SSH
        ]

        for pattern in patterns:
            match = re.match(pattern, url)
            if match:
                return match.groups()

        raise ValueError("Invalid GitHub repository URL format")

    def create_issue(self, owner: str, repo: str, title: str, body: str, labels: list = None) -> dict:
        """Create a new issue in the repository."""
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues"
        data = {
            "title": title,
            "body": body,
            "labels": labels or []
        }
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_repo_prs(self, owner: str, repo: str, state: str = "open") -> list:
        """Get pull requests from a repository."""
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls"
        params = {"state": state}
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> list:
        """Get files changed in a pull request."""
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def get_issue(self, owner: str, repo: str, issue_number: int) -> dict:
        """Get a specific issue from a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number

        Returns:
            Issue data as a dict
        """
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues/{issue_number}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()
