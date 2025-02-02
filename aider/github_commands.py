"""GitHub issue integration commands for aider."""

from .github_issues import GitHubIssueClient
from .issue_parser import IssueParser
from .problem_generator import ProblemGenerator

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
        self.generator = ProblemGenerator()

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
        issue = self.client.get_repo_issues(
            owner,
            repo,
            state="open"
        )[0]

        comments = []
        if with_comments:
            comments = self.client.get_issue_comments(owner, repo, issue_number)

        # Parse and generate problem
        problem_def = self.parser.parse_issue(issue, comments)
        aider_problem = self.generator.generate_problem(
            problem_def,
            additional_context={"repository": f"{owner}/{repo}"}
        )

        # Run aider on the problem
        instructions = aider_problem.task
        if aider_problem.context:
            instructions = f"{aider_problem.context}\n\n{instructions}"
        self.coder.run(with_message=instructions, preproc=False)

        # Track files that need attention
        for file in aider_problem.files_to_modify:
            self.coder.add_file(file)

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
