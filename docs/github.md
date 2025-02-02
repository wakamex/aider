# GitHub Integration

Aider provides seamless integration with GitHub through pull request creation, issue management, and customizable personalities.

## Personality

Aider can apply a custom personality to your GitHub interactions (PR descriptions, comments, etc). The personality is loaded from your personal `personality` repository on GitHub.

### Setup

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

You can control the personality feature through:

1. Environment variable: `AIDER_PERSONALITY_ENABLED=true|false`
2. Configuration file: `.aider.conf.yml`

Example `.aider.conf.yml`:
```yaml
github:
  personality:
    enabled: true
```

### Testing

To test the personality feature:

1. Set up required environment variables (pick a good free model from `model_prices.py`):
   ```bash
   export GEMINI_API_KEY=your_api_key
   export AIDER_TEST_MODEL=gemini/gemini-2.0-flash-exp
   ```

2. Run the integration tests:
   ```bash
   .venv/bin/python -m pytest tests/test_github_integration.py -r A --verbosity=2 --log-cli-level=INFO
   ```

The tests will create a temporary GitHub repository and verify that your personality is correctly applied to:
- PR descriptions
- Issue comments
- Progress updates

## Configuration

### GitHub Token

You can configure your GitHub token in three ways (in order of precedence):

1. Direct token input when initializing the client
2. Environment variable: `GITHUB_TOKEN`
3. Configuration file: `.aider.conf.yml`

Example `.aider.conf.yml`:
```yaml
github:
  token: your_github_token
  rate_limit:
    max_per_page: 100
    default_per_page: 30
```

## Commands

### `/issue` - Process a Single Issue

Process a specific GitHub issue by its number. Supports two formats:

1. Repository shorthand:
```
/issue owner/repo#123
```

2. Full GitHub URL:
```
/issue https://github.com/owner/repo/issues/123
```

### `/issues` - List Repository Issues

List all open issues in a GitHub repository. Supports two formats:

1. Repository shorthand:
```
/issues owner/repo
```

2. Full GitHub URL:
```
/issues https://github.com/owner/repo
```

### `/comment` - Add a Comment to an Issue

Add a comment to a specific GitHub issue:

1. Repository shorthand:
```
/comment owner/repo#123 Your comment text here
```

2. Full GitHub URL:
```
/comment https://github.com/owner/repo/issues/123 Your comment text here
```

### `/update` - Update an Issue

Update a GitHub issue's state, title, body, or labels:

```
# Close an issue
/update owner/repo#123 --state closed

# Update title
/update owner/repo#123 --title "New Title"

# Update description
/update owner/repo#123 --body "New description"

# Update labels
/update owner/repo#123 --labels bug,feature

# Multiple updates at once
/update owner/repo#123 --state closed --labels done,fixed
```

You can also use the full GitHub URL format:
```
/update https://github.com/owner/repo/issues/123 --state closed
```

### `/pr` - Create a Pull Request

Create a pull request from your current branch:

1. Repository shorthand:
```
# Basic PR
/pr owner/repo --title "Add new feature"

# PR with description
/pr owner/repo --title "Add new feature" --body "Implemented feature X"

# PR with custom base branch
/pr owner/repo --title "Add new feature" --base develop

# Draft PR
/pr owner/repo --title "WIP: Add new feature" --draft
```

2. Full GitHub URL:
```
/pr https://github.com/owner/repo --title "Add new feature"
```

The command will automatically use your current branch as the source branch.

### `/prcomment` - Comment on a Pull Request

Add a comment to an existing pull request:

1. Repository shorthand:
```
/prcomment owner/repo#123 Your comment text here
```

2. Full GitHub URL:
```
/prcomment https://github.com/owner/repo/pull/123 Your comment text here
```

### `/prupdate` - Update PR Progress

Add or update progress information on a pull request. This will maintain a single progress comment that gets updated with each change:

1. Repository shorthand:
```
/prupdate owner/repo#123 Added new feature X
```

2. Full GitHub URL:
```
/prupdate https://github.com/owner/repo/pull/123 Fixed bug Y
```

The progress will be tracked in a single comment that gets updated with each change, including timestamps.

## Rate Limiting

Rate limits can be configured in `.aider.conf.yml`:

```yaml
github:
  rate_limit:
    max_per_page: 100    # Maximum items per page (max: 100)
    default_per_page: 30 # Default items per page
```

The client will automatically respect these limits when making API requests.
