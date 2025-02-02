# GitHub Integration Tasks

This project extends aider to work with GitHub pull requests and issues.

## Tasks

### 1. GitHub Integration Module
- [x] Create `github_issues.py` module
- [x] Implement GitHub API authentication handling
- [x] Add PR creation functionality
- [x] Add PR comment functionality
- [x] Add rate limiting and pagination handling
- [x] Write tests for GitHub API integration
- [x] Add token configuration via env var or direct input
- [x] Add repository URL parsing support

### 2. Commands and Configuration
- [x] Add `/pr` command for PR creation
- [x] Add `/prcomment` command for PR comments
- [x] Add configuration options for GitHub integration
- [x] Add GitHub token configuration
- [x] Add rate limit settings
- [x] Add configuration file support
- [x] Write integration tests

### 3. Documentation
- [x] Add user documentation for commands
- [x] Add developer documentation for modules
- [x] Document configuration options
- [x] Add usage examples

### 4. Integration Features
- [x] Add automatic PR updates with progress
- [x] Add file change tracking
- [x] Add personality-driven comments
- [x] Add LLM integration for comment styling
- [x] Add personality configuration

## Dependencies
- requests: HTTP client for GitHub API
- yaml: Configuration file parsing

## Guidelines
- All code changes follow minimal and concise design principles
- Focus on maintainability and readability
- Error handling with user-friendly messages
- Token configuration via GITHUB_TOKEN environment variable
- Rate limit handling with automatic tracking
- File changes tracked automatically via git commands

## Personality Integration

The personality integration feature allows aider to add unique flair to GitHub interactions based on a user-defined personality. This feature uses LLM to generate contextually appropriate, personality-driven content while preserving the original message.

### Integration Points
Commands to enhance with personality:
- `/prcomment` - When adding comments to PRs
- `/prupdate` - When updating PR progress
- `/comment` - When commenting on issues
- `/pr` - When creating PR descriptions
- `/update` - When updating issues

Methods in GitHubIssueClient:
- `create_pr_comment()` - Add flair to PR comments
- `create_issue_comment()` - Style issue comments
- `update_pr_progress()` - Enhance progress updates
- `create_pull_request()` - Add personality to PR descriptions
- `update_issue()` - Style issue updates

### Scope
- PR Comments: Add personality to comments on pull requests
- Issue Comments: Style issue comments with personality
- PR Progress Updates: Include personality in progress tracking
- PR Descriptions: Add flair to initial PR descriptions
- Issue Updates: Style issue updates with personality

### Implementation
- [x] PersonalityManager class to handle personality loading and application
- [x] LLM integration for generating personality-driven content
- [x] Configuration via .aider.conf.yml and personality repository
- [x] Fallback mechanisms for graceful degradation
- [x] Context-aware personality application

### Configuration
Users can define their personality by:
1. Creating a personality repository with a README.md
2. Configuring personality settings in .aider.conf.yml:
   ```yaml
   github:
     personality:
       enabled: true
   ```
3. Using `/personality toggle` to enable/disable at runtime

### Error Handling
- [x] Graceful fallback to original content on LLM failures
- [x] Maximum length limits for personality additions (comments should be brief enough to not distract from the content)
- [x] Rate limiting consideration for LLM calls
- [x] Retry strategy for failed LLM requests

### Testing Strategy
- [x] Personality mechanism verified in test_github_integration.py
- [x] Integration points tested through existing GitHub client tests

### User Experience
- [x] `/personality toggle` to enable/disable temporarily
- [x] Clear feedback when personality is applied (✨ indicator)

## Aider commands for reference
/model Switch to a new LLM
/chat-mode Switch to a new chat mode
/models Search the list of available models
/web Scrape a webpage, convert to markdown and send in a message
/commit Commit edits to the repo made outside the chat (commit message optional)
/lint Lint and fix in-chat files or all dirty files if none in chat
/clear Clear the chat history
/reset Drop all files and clear the chat history
/tokens Report on the number of tokens used by the current chat context
/undo Undo the last git commit if it was done by aider
/diff Display the diff of changes since the last message
/add Add files to the chat so aider can edit them or review them in detail
/drop Remove files from the chat session to free up context space
/git Run a git command (output excluded from chat)
/test Run a shell command and add the output to the chat on non-zero exit code
/run Run a shell command and optionally add the output to the chat (alias: !)
/exit Exit the application
/quit Exit the application
/ls List all known files and indicate which are included in the chat session
/help Ask questions about aider
/ask Ask questions about the code base without editing any files. If no prompt provided, switches to ask mode.
/code Ask for changes to your code. If no prompt provided, switches to code mode.
/architect Enter architect/editor mode using 2 different models. If no prompt provided, switches to architect/editor mode.
/voice Record and transcribe voice input
/paste Paste image/text from the clipboard into the chat. Optionally provide a name for the image.
/read-only Add files to the chat that are for reference only, or turn added files to read-only
/map Print out the current repository map
/map-refresh Force a refresh of the repository map
/settings Print out the current settings
/load Load and execute commands from a file
/save Save commands to a file that can reconstruct the current chat session's files
/multiline-mode Toggle multiline mode (swaps behavior of Enter and Meta+Enter)
/copy Copy the last assistant message to the clipboard
/report Report a problem by opening a GitHub Issue
/editor Open an editor to write a prompt
/copy-context Copy the current chat context as markdown, suitable to paste into a web UI
/issue Process a GitHub issue by number: /issue owner/repo#123 or /issue https://github.com/owner/repo/issues/123
/issues List open issues from a GitHub repository: /issues owner/repo or /issues https://github.com/owner/repo
/comment Add a comment to a GitHub issue.
/update Update a GitHub issue.
/pr Create a pull request.
/prupdate Update progress on a pull request.
/prcomment Add a comment to a pull request.