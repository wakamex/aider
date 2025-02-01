"""GitHub issue integration for aider.

This module handles fetching and processing GitHub issues to be used as problem definitions
for aider's AI-assisted coding.
"""

import os
import time
from typing import Dict, List, Optional
import requests
from urllib.parse import urlparse

class GitHubIssueClient:
    """Client for interacting with GitHub Issues API."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = "https://api.github.com",
        verify_ssl: bool = True,
    ):
        """Initialize GitHub client.

        Args:
            token: GitHub API token. If not provided, will look for GITHUB_TOKEN env var
            base_url: Base URL for GitHub API
            verify_ssl: Whether to verify SSL certificates
        """
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise ValueError(
                "GitHub token required. Either pass token parameter or set GITHUB_TOKEN environment variable."
            )

        self.base_url = base_url
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        })

        # Rate limit tracking
        self.rate_limit = None
        self.rate_limit_reset = None

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Update rate limit info from response headers."""
        self.rate_limit = int(response.headers.get("X-RateLimit-Remaining", 0))
        self.rate_limit_reset = int(response.headers.get("X-RateLimit-Reset", 0))

        if self.rate_limit == 0:
            sleep_time = max(self.rate_limit_reset - time.time(), 0)
            time.sleep(sleep_time)

    def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> requests.Response:
        """Make a GitHub API request with rate limit handling."""
        response = self.session.request(
            method,
            url,
            verify=self.verify_ssl,
            **kwargs
        )
        self._handle_rate_limit(response)
        response.raise_for_status()
        return response

    def get_repo_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        since: Optional[str] = None,
        page: int = 1,
        per_page: int = 30,
    ) -> List[Dict]:
        """Fetch issues from a GitHub repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            state: Issue state (open/closed/all)
            labels: List of label names to filter by
            since: ISO 8601 timestamp to filter by updated time
            page: Page number for pagination
            per_page: Number of items per page
            
        Returns:
            List of issue dictionaries
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        params = {
            "state": state,
            "page": page,
            "per_page": per_page,
        }
        if labels:
            params["labels"] = ",".join(labels)
        if since:
            params["since"] = since

        response = self._make_request("GET", url, params=params)
        return response.json()

    def get_issue_comments(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        page: int = 1,
        per_page: int = 30,
    ) -> List[Dict]:
        """Fetch comments for a specific issue.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number
            page: Page number for pagination
            per_page: Number of items per page
            
        Returns:
            List of comment dictionaries
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments"
        params = {
            "page": page,
            "per_page": per_page,
        }

        response = self._make_request("GET", url, params=params)
        return response.json()

    @staticmethod
    def parse_repo_url(url: str) -> tuple[str, str]:
        """Parse owner and repo name from a GitHub repository URL.
        
        Args:
            url: GitHub repository URL
            
        Returns:
            Tuple of (owner, repo)
            
        Raises:
            ValueError: If URL is not a valid GitHub repository URL
        """
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split("/") if p]

            if len(path_parts) < 2:
                raise ValueError

            return path_parts[0], path_parts[1]

        except Exception as exc:
            raise ValueError(
                f"Invalid GitHub repository URL: {url}. "
                "Expected format: https://github.com/owner/repo"
            ) from exc
