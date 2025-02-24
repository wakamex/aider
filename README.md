# Aider GitHub Integration Guide

## Usage examples

implements simple request:
![image](https://github.com/user-attachments/assets/091dcc0a-c3e0-4db1-8406-0f67dea2e59a)
![image](https://github.com/user-attachments/assets/e09caf0d-f549-4744-8513-c5f8287a2da3)

This guide covers both user features and development details of Aider's GitHub integration.

## Architecture Overview

The GitHub integration consists of three main components:

1. `GitHubIssueClient` - Core API client for GitHub interactions
2. GitHub commands in `Commands` class - User-facing commands
3. Configuration management - Handles settings and credentials
4. GitHub Daemon - Automated issue processing (optional)

## User Features

### Personality

Aider can apply a custom personality to your GitHub interactions (PR descriptions, comments, etc). The personality is loaded from your personal `personality` repository on GitHub.

#### Setup

1. Create a repository named `personality` in your GitHub account
2. Add a `README.md` file that describes your desired personality
3. The personality will be automatically applied to all GitHub interactions

Example `README.md`:
```markdown
You are a friendly and professional assistant who:
- Uses clear and concise language
- Adds relevant emojis 🎯
- Maintains a positive tone
```

### Configuration

#### GitHub Token

You can configure your GitHub token in three ways (in order of precedence):

1. Direct token input when initializing the client
2. Environment variable: `GITHUB_TOKEN`
3. Configuration file: `.aider.conf.yml`

Example `.aider.conf.yml`:
```yaml
github:
  token: your_github_token
  personality:
    enabled: true
  rate_limit:
    max_per_page: 100
    default_per_page: 30
```

### Commands

#### `/issue` - Process a Single Issue

Process a specific GitHub issue by its number:
```
/issue owner/repo#123
/issue https://github.com/owner/repo/issues/123
```

#### `/issues` - List Repository Issues
```
/issues owner/repo
/issues https://github.com/owner/repo
```

#### `/comment` - Add a Comment
```
/comment owner/repo#123 Your comment text here
/comment https://github.com/owner/repo/issues/123 Your comment text here
```

#### `/update` - Update an Issue
```
/update owner/repo#123 --state closed
/update owner/repo#123 --title "New Title" --labels bug,feature
```

#### `/pr` - Create a Pull Request
```
/pr owner/repo --title "Add new feature" [--body "Description"] [--base main] [--draft]
```

#### `/prcomment` and `/prupdate` - PR Interactions
```
/prcomment owner/repo#123 Your comment here
/prupdate owner/repo#123 Added new feature X  # Updates progress tracking comment
```

## GitHub Daemon

The GitHub daemon (`scripts/github_daemon.py`) provides automated processing of GitHub issues.

### Features
- Continuous monitoring of repository issues
- Processes only new, unhandled issues
- Label-based filtering
- Configurable polling intervals
- State persistence across restarts
- Error handling and recovery

### Usage

```bash
# Basic usage - monitor all issues
.venv/bin/python scripts/github_daemon.py owner/repo

# Monitor specific labels with custom poll interval
.venv/bin/python scripts/github_daemon.py owner/repo \
    --labels "bug,enhancement" \
    --poll-interval 300

# With verbose logging
.venv/bin/python scripts/github_daemon.py owner/repo --verbose
```

### Configuration

Command line options:
- `--work-dir`: Working directory (default: current)
- `--model`: Model to use (default: gpt-3.5-turbo)
- `--labels`: Only process issues with these labels
- `--poll-interval`: Seconds between polls (default: 60)
- `--error-wait`: Seconds to wait after error (default: 300)
- `--verbose`: Enable verbose logging

### State Management

The daemon maintains a `.processed_issues.json` file to track which issues have been handled, ensuring:
- No duplicate processing
- State persistence across restarts
- Safe concurrent operation

## Development Details

### GitHubIssueClient

Core API client in `github_issues.py`:
```python
class GitHubIssueClient:
    def get_repo_issues(self, owner: str, repo: str, ...) -> List[Dict]
    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> List[Dict]
```

### Testing

Three test categories:
1. Client Tests: API interactions, rate limiting
2. Command Tests: Command parsing, error handling
3. Integration Tests: End-to-end functionality

Run tests:
```bash
# Set up test environment
export GEMINI_API_KEY=your_api_key
export AIDER_TEST_MODEL=gemini/gemini-2.0-flash-exp

# Run tests
.venv/bin/python -m pytest tests/test_github_integration.py -r A --verbosity=2 --log-cli-level=INFO
```

### Contributing

When adding features:
1. Follow existing patterns
5. Use type hints and docstrings
2. Add comprehensive tests
3. Update documentation
4. Consider rate limiting
