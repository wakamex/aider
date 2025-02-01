"""GitHub Issue Client for interacting with GitHub's API."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import yaml
import re

# Constants for GitHub API
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"
DEFAULT_CONFIG = {
    "rate_limit": {
        "max_per_page": 100,
        "default_per_page": 30,
    }
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

class GitHubIssueClient:
    """Client for interacting with GitHub Issues API."""

    def __init__(self, token: Optional[str] = None, config: Optional[Dict] = None):
        """Initialize the GitHub client.
        
        Args:
            token: GitHub API token. If not provided, will try to read from GITHUB_TOKEN env var
                  or .aider.conf.yml github.token
            config: Configuration dict. If not provided, will try to read from .aider.conf.yml
        """
        self.config = DEFAULT_CONFIG.copy()
        
        # Try to load config from .aider.conf.yml
        conf_path = Path(".aider.conf.yml")
        yaml_config = {}
        if conf_path.exists():
            try:
                with open(conf_path) as f:
                    yaml_config = yaml.safe_load(f) or {}
                    if "github" in yaml_config:
                        self.config = merge_configs(self.config, yaml_config["github"])
            except Exception:
                pass  # Ignore config file errors
        
        # Update with provided config
        if config:
            self.config = merge_configs(self.config, config)
        
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
