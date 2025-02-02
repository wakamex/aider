"""GitHub issue integration commands for aider."""

from .github_issues import GitHubIssueClient
from .issue_parser import IssueParser

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
        self.parser = IssueParser()

    def _ensure_client(self) -> None:
        """Ensure GitHub client is initialized."""
        if not self.client:
            self.client = GitHubIssueClient()

    def process_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        with_comments: bool = True
    ) -> None:
        """Process a GitHub issue and prepare it for aider.

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue number to process
            with_comments: Whether to include issue comments
        """
        self._ensure_client()

        # Fetch issue and comments
        issue = self.client.get_issue(owner, repo, issue_number)
        if not issue:
            raise Exception(f"Issue {issue_number} not found")

        comments = []
        if with_comments:
            comments = self.client.get_issue_comments(owner, repo, issue_number)

        # Parse issue and build instructions
        problem_def = self.parser.parse_issue(issue, comments)
        
        # Build task description
        instructions = f"{problem_def.title}\n\n"
        if problem_def.description:
            instructions += f"{problem_def.description}\n\n"
            
        # Add relevant context
        if problem_def.context:
            for key, value in problem_def.context.items():
                if key in ['context', 'background']:
                    instructions += f"\nBackground:\n{value}\n"
                elif key == 'current behavior':
                    instructions += f"\nCurrent Behavior:\n{value}\n"
                elif key == 'additional_info':
                    instructions += f"\nAdditional Information:\n{value}\n"
                    
        # Add repository context
        instructions += f"\nRepository: {owner}/{repo}"

        # Run aider with the instructions
        self.coder.run(instructions)

        # Add any referenced files
        for ref in problem_def.code_references:
            if ref.file:
                self.coder.add_file(ref.file)

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
