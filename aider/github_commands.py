"""GitHub issue integration commands for aider."""

import logging
from .github_issues import GitHubIssueClient

class GitHubCommands:
    """Commands for working with GitHub issues in aider."""

    def __init__(self, io, coder):
        """Initialize GitHub commands.

        Args:
            io: Aider IO interface
            coder: Aider coder instance
        """
        self.io = io
        self.coder = coder
        self.client = None

    def _ensure_client(self) -> None:
        """Ensure GitHub client is initialized."""
        if not self.client:
            self.client = GitHubIssueClient()

    def process_issue(self, owner: str, repo: str, issue_number: int, with_comments: bool = True) -> None:
        """Process a GitHub issue and prepare it for aider."""
        self._ensure_client()

        # Get issue details
        issue = self.client.get_issue(owner, repo, issue_number)
        if not issue:
            raise Exception(f"Issue {issue_number} not found")

        # Get issue comments if requested
        comments = []
        if with_comments:
            comments = self.client.get_issue_comments(owner, repo, issue_number)

        # Build instruction string from issue title and body
        instruction = (
            f"Problem: {issue['title']}\n\n"
            f"{issue['body']}\n\n"
            "Note: This is an automated session. Please create all necessary files in one go. "
            "Do not ask for files to be added to the chat - just create them.\n"
            "If you need to create multiple files, do it all at once.\n"
        )

        # Add comments if any
        if comments:
            instruction += "\nAdditional context from comments:\n"
            for comment in comments:
                instruction += f"\n{comment['body']}\n"

        logging.info(f"Sending instruction to coder: {instruction}")

        # Send instruction to coder
        response = self.coder.run(instruction)
        logging.info(f"Coder response: {response}")

    def process_repo_issue(
        self,
        repo_url: str,
        issue_number: int,
        with_comments: bool = True
    ) -> None:
        """Process an issue using repository URL.

        Args:
            repo_url: GitHub repository URL
            issue_number: Issue number to process
            with_comments: Whether to include issue comments
        """
        self._ensure_client()
        owner, repo = self.client.parse_repo_url(repo_url)
        self.process_issue(owner, repo, issue_number, with_comments)
