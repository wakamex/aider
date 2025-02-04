#!/usr/bin/env python3

import json
import argparse
import logging
import traceback
from pathlib import Path
import os
import subprocess

from aider.github_commands import GitHubCommands
from aider.io import InputOutput
from aider.coders import Coder
from aider import models
from aider.github_issues import GitHubIssueClient

def clone_repo(owner: str, repo: str, repo_dir: Path, token: str) -> bool:
    """Clone a GitHub repository."""
    clone_url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
    try:
        logging.info(f"Cloning {owner}/{repo} to {repo_dir}")
        subprocess.run(["git", "clone", "--depth=1", clone_url, str(repo_dir)], check=True, capture_output=True)

        # Verify remote is set up correctly
        logging.info("Checking git remote")
        remotes = subprocess.run(["git", "remote", "-v"], cwd=repo_dir, check=True, capture_output=True, text=True)
        logging.info(f"Git remotes: {remotes.stdout}")

        # Set up remote if needed
        if "origin" not in remotes.stdout:
            logging.info("Setting up git remote")
            subprocess.run(["git", "remote", "add", "origin", clone_url], cwd=repo_dir, check=True)

        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Clone error: {e.stderr}")
        return False

def run_git(args, cwd):
    try:
        logging.info(f"Running git {' '.join(args)} in {cwd}")
        result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=True)
        logging.info(f"Git output: {result.stdout}")
        if result.stderr:
            logging.info(f"Git stderr: {result.stderr}")
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Git error: {e.stderr}")
        if e.stdout:
            logging.error(f"Git error stdout: {e.stdout}")
        raise

def process_issue_real(
    owner: str,
    repo: str,
    issue_number: int,
    work_dir: Path,
    model_name: str,
    verbose: bool = False,
    with_comments: bool = True,
    no_git: bool = False,
) -> dict:
    """Process a GitHub issue using aider."""
    # Set up working directory for this issue
    issue_dir = work_dir / f"{owner}-{repo}-{issue_number}"
    issue_dir.mkdir(parents=True, exist_ok=True)

    # Set up repository directory
    repo_dir = issue_dir / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    # Set up results file
    results_file = issue_dir / ".aider.results.json"
    results = {}

    try:
        # Initialize GitHub client
        client = GitHubIssueClient()

        # Get issue details
        issue = client.get_issue(owner, repo, issue_number)
        if not issue:
            raise Exception(f"Issue {issue_number} not found")

        # Get issue comments if requested
        comments = []
        if with_comments:
            comments = client.get_issue_comments(owner, repo, issue_number)

        # Clone repository
        logging.info(f"Cloning repository to {repo_dir}")
        if not clone_repo(owner, repo, repo_dir, client.token):
            raise Exception("Failed to clone repository")

        # Create branch for issue
        branch_name = f"fix-issue-{issue_number}"
        if not no_git:
            run_git(["checkout", "-b", branch_name], cwd=repo_dir)

        # Set up aider components
        io = InputOutput(
            pretty=True,
            yes=True,
            chat_history_file=issue_dir / ".aider.chat.history.md"
        )

        main_model = models.Model(model_name)

        # Change to repo directory before creating coder
        logging.info(f"Changing to directory: {repo_dir}")
        os.chdir(repo_dir)

        # Configure git user before coder tries to commit
        logging.info("Configuring git user")
        client.configure_git_user(repo_dir)

        coder = Coder.create(
            main_model,
            main_model.edit_format,
            io,
            fnames=[],  # Let aider discover files
            use_git=not no_git,  # We'll handle git operations
            stream=False,
            verbose=verbose,
            cache_prompts=True,
            suggest_shell_commands=False,
        )

        # Initialize commands
        commands = GitHubCommands(io, coder)
        commands._ensure_client()

        # Process the issue
        commands.process_issue(owner, repo, issue_number, with_comments)

        # Check if any changes were made
        logging.info("Checking git status")
        status = run_git(["status", "--porcelain"], cwd=repo_dir)
        logging.info(f"Git status: {status}")

        # Check for both tracked and untracked changes
        has_changes = bool(status) and any(line.strip() for line in status.splitlines())
        logging.info(f"Has changes: {has_changes}, no_git: {no_git}")
        if has_changes:
            # Stage and commit changes
            if not no_git:
                # Add all changes including untracked files
                logging.info("Adding changes")
                run_git(["add", "-A"], cwd=repo_dir)
                commit_msg = f"Fix issue #{issue_number}: {issue['title']}\n\nFixes #{issue_number}"
                logging.info("Committing changes")
                run_git(["commit", "-m", commit_msg], cwd=repo_dir)

                # Push changes
                logging.info("Pushing changes")
                run_git(["push", "-u", "origin", branch_name], cwd=repo_dir)

                # Create pull request
                logging.info("Creating pull request")
                pr = client.create_pull_request(
                    owner,
                    repo,
                    title=f"Fix issue #{issue_number}: {issue['title']}",
                    body=f"Fixes #{issue_number}",
                    head=branch_name,
                    base="main"
                )
                results["pull_request"] = pr
                logging.info(f"Created PR: {pr}")

        results["success"] = True

    except Exception as e:
        results["success"] = False
        results["error"] = str(e)
        logging.error(f"Error: {e}")
        raise

    finally:
        # Save results
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

    return results

def process_issue(owner: str, repo: str, issue_number: int, *args, **kwargs):
    """Wrapper for process_issue_real that handles exceptions. Like run_test in benchmark.py."""
    try:
        return process_issue_real(owner, repo, issue_number, *args, **kwargs)
    except Exception as err:
        logging.info("=" * 40)
        logging.info("Issue processing failed")
        logging.info(err)
        traceback.print_exc()

        work_dir = kwargs.get("work_dir")
        if work_dir:
            issue_dir = work_dir / f"{owner}-{repo}-{issue_number}"
            results_fname = issue_dir / ".aider.results.json"
            results_fname.write_text(json.dumps({"exception": str(err)}))

def main():
    """Main entry point for GitHub automation."""
    parser = argparse.ArgumentParser(description="Process GitHub issues with aider")
    parser.add_argument("repo", help="Repository in format owner/repo")
    parser.add_argument("--labels", help="Only process issues with these labels (comma separated)")
    parser.add_argument("--work-dir", type=Path, help="Working directory", default=Path.cwd())
    parser.add_argument("--model", help="Model name to use", default="gpt-3.5-turbo")
    parser.add_argument("--no-git", action="store_true", help="Don't manage git operations")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # Parse owner/repo
    owner, repo = args.repo.split("/")

    # Get list of issues
    client = GitHubIssueClient()
    issues = client.get_repo_issues(owner, repo)

    # Filter by labels if specified
    if args.labels:
        labels = set(args.labels.split(","))
        issues = [i for i in issues if any(l["name"] in labels for l in i["labels"])]

    # Process each issue
    for issue in issues:
        process_issue_real(
            owner,
            repo,
            issue["number"],
            args.work_dir,
            args.model,
            verbose=args.verbose,
            no_git=args.no_git
        )

if __name__ == "__main__":
    main()
