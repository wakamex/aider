#!/usr/bin/env python3

import argparse
import json
import logging
import time
from pathlib import Path

from aider.github_issues import GitHubIssueClient
from aider.github_automation import process_issue

# Constants
DEFAULT_POLL_INTERVAL = 60  # seconds
DEFAULT_ERROR_WAIT = 300  # seconds
DEFAULT_MIN_BALANCE = 5.0  # USD
PROCESSED_ISSUES_FILE = ".processed_issues.json"

def setup_logging(level=logging.INFO):
    """Configure logging with consistent format."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()],
    )

def load_processed_issues(work_dir: Path) -> set:
    """Load set of already processed issue numbers."""
    processed_file = work_dir / PROCESSED_ISSUES_FILE
    if processed_file.exists():
        return set(json.loads(processed_file.read_text()))
    return set()

def save_processed_issues(work_dir: Path, processed: set):
    """Save set of processed issue numbers."""
    processed_file = work_dir / PROCESSED_ISSUES_FILE
    processed_file.write_text(json.dumps(list(processed)))

def process_new_issues(
    owner: str,
    repo: str,
    work_dir: Path,
    model: str,
    labels: set = None,
    client=None,
    processed: set = None,
):
    """Process any new issues that haven't been handled yet."""
    if client is None:
        client = GitHubIssueClient()
    if processed is None:
        processed = set()

    # Get list of open issues
    issues = client.get_repo_issues(owner, repo, state="open")
    
    # Filter by labels if specified
    if labels:
        issues = [i for i in issues if any(l["name"] in labels for l in i["labels"])]

    # Process new issues
    for issue in issues:
        issue_num = issue["number"]
        if issue_num not in processed:
            logging.info("Processing new issue #%d: %s", issue_num, issue['title'])
            try:
                process_issue(
                    owner,
                    repo,
                    issue_num,
                    work_dir=work_dir,
                    model_name=model,
                    github_client=client,
                )
                processed.add(issue_num)
                save_processed_issues(work_dir, processed)
                logging.info("Successfully processed issue #%d", issue_num)
            except Exception as e:
                logging.error("Failed to process issue #%d: %s", issue_num, e)

def main():
    """Main daemon loop for processing GitHub issues."""
    parser = argparse.ArgumentParser(description="GitHub issue processing daemon")
    parser.add_argument("repo", help="Repository in format owner/repo")
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Working directory",
        default=Path.cwd(),
    )
    parser.add_argument(
        "--model",
        help="Model name to use",
        default="gpt-3.5-turbo",
    )
    parser.add_argument(
        "--labels",
        help="Only process issues with these labels (comma separated)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        help=f"Seconds between polls (default: {DEFAULT_POLL_INTERVAL})",
        default=DEFAULT_POLL_INTERVAL,
    )
    parser.add_argument(
        "--error-wait",
        type=int,
        help=f"Seconds to wait after error (default: {DEFAULT_ERROR_WAIT})",
        default=DEFAULT_ERROR_WAIT,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    # Setup logging
    setup_logging(level=logging.DEBUG if args.verbose else logging.INFO)

    # Parse owner/repo
    owner, repo = args.repo.split("/")

    # Parse labels
    labels = set(args.labels.split(",")) if args.labels else None

    # Load already processed issues
    processed_issues = load_processed_issues(args.work_dir)

    # Setup GitHub client
    client = GitHubIssueClient()

    logging.info(
        "Starting GitHub daemon for %s/%s (poll: %ds, labels: %s)",
        owner, repo, args.poll_interval, labels or 'all'
    )

    while True:
        try:
            process_new_issues(
                owner,
                repo,
                args.work_dir,
                args.model,
                labels=labels,
                client=client,
                processed=processed_issues,
            )
            time.sleep(args.poll_interval)

        except KeyboardInterrupt:
            logging.info("Shutting down...")
            break

        except Exception as e:
            logging.error("Error in main loop: %s", e)
            time.sleep(args.error_wait)

if __name__ == "__main__":
    main()
