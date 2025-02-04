# GitHub Integration Development Guide

This document describes the architecture and implementation details of Aider's GitHub integration.

## Architecture

The GitHub integration consists of three main components:

1. `GitHubIssueClient` - Core API client
2. GitHub commands in `Commands` class
3. Configuration management

### GitHubIssueClient

Located in `github_issues.py`, this class handles all GitHub API interactions:

```python
class GitHubIssueClient:
    def __init__(self, token: Optional[str] = None, config: Optional[Dict] = None):
        # Initialize with token and optional config
        pass

    def get_repo_issues(self, owner: str, repo: str, ...) -> List[Dict]:
        # Fetch repository issues
        pass

    def get_issue_comments(self, owner: str, repo: str, issue_number: int, ...) -> List[Dict]:
        # Fetch issue comments
        pass
```

### Configuration Management

Configuration follows a priority order:
1. Direct configuration (highest priority)
2. Environment variables
3. Configuration file (lowest priority)

Example configuration merge:
```python
def merge_configs(base: Dict, update: Dict) -> Dict:
    """Deep merge two configs, with update taking precedence."""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result
```

### Commands Integration

GitHub commands are implemented in the `Commands` class:

```python
def cmd_issue(self, args: str) -> Optional[str]:
    """Process a GitHub issue."""
    # Parse issue reference and process
    pass

def cmd_issues(self, args: str) -> Optional[str]:
    """List repository issues."""
    # Parse repository reference and list issues
    pass
```

## Testing

Tests are organized into three categories:

1. Client Tests
   - Token configuration
   - Rate limit handling
   - API interactions

2. Command Tests
   - Command parsing
   - Error handling
   - Integration with client

3. Configuration Tests
   - Config file loading
   - Config merging
   - Token precedence

## Contributing

When adding new features:

1. Follow the existing pattern for command implementation
2. Add comprehensive tests
3. Update both user and developer documentation
4. Keep rate limiting in mind
5. Use type hints and docstrings
