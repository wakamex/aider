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

### 5. Automation Features
- [-] Create automation script
  - [x] Use benchmark.py's pattern of setting up files first, then running coder
  - [x] Simplify to use direct `coder.run()` with instructions
  - [x] Keep the script foreground-style like benchmark.py
  - [x] Setup clean working directory for each issue
  - [x] Add shallow clone of repository
  - [x] Create branch per issue
  - [x] Test branch creation and git operations
  - [x] Add commit after changes
  - [x] Add PR creation
  - [x] Add PR description from results
  - [x] Wrap core logic in try/except
  - [x] Store results in JSON format
  - [x] Include error details in output
  - [-] Add failure reporting to issue
  - [ ] Add retry mechanism for transient failures
- [-] Extend problem processing
  - [x] Add clean workspace per issue
  - [x] Add PR creation on success
  - [-] Add failure reporting to issue
- [-] Add automation settings
  - [x] Add issue label filters
  - [x] Add repository list
  - [ ] Add retry settings
  - [ ] Add configurable git settings (branch prefix, PR template)
- [ ] Add OpenRouter auto-top-up
  - [ ] Add balance check to existing polling loop
  - [ ] Add simple config for min balance and top-up amount
  - [ ] Integrate with OpenRouter's direct crypto payment API
  - [ ] Add basic error notification

## Files
.gitignore: Specifies intentionally untracked files that Git should ignore, including a new 'personality/' directory.
.pylintrc: New configuration file for Pylint, a Python source code analyzer, with disabled messages, naming styles, and a regular expression for ignoring long lines with URLs.
TASK.md: New markdown file outlining tasks, guidelines, and integration points for extending aider to work with GitHub pull requests and issues.
aider/commands.py: Implements chat commands, including new GitHub related commands (/issue, /issues, /comment, /update, /pr, /prupdate, /prcomment, /personality) and refactors existing ones.
aider/github_automation.py: New file implementing automation for processing GitHub issues, including cloning, branching, committing, and creating pull requests.
aider/github_commands.py: New file containing the `GitHubCommands` class, which handles issue processing logic and interacts with the `GitHubIssueClient`.
aider/github_issues.py: New module implementing `GitHubIssueClient` for interacting with the GitHub API, handling authentication, rate limiting, and various issue/PR operations. Includes `PersonalityManager`.
aider/io.py: Input/Output handling, including chat history, user prompts, and console output, updated with logging.
aider/llm.py: Defines LazyLiteLLM and adds an LLM class for response generation.
aider/main.py: Main entry point for the aider CLI, handling argument parsing, configuration loading, and running the chat loop. Added logging setup.
docs/development/github.md: New developer documentation file describing the architecture and implementation of Aider's GitHub integration.
docs/github.md: New user documentation file for Aider's GitHub integration features, including personality, configuration, commands, and rate limiting.
model_prices.py: New script to fetch and display model prices from a litellm URL in a table.
requirements/requirements-dev.in: Adds the `responses` library to the development requirements, used for mocking HTTP requests in tests.
tests/test_github_commands.py: New test file for the GitHub-related commands in `aider/commands.py` and basic client functionality.
tests/test_github_integration.py: New file with integration tests for Aider's GitHub functionality, creating repositories, issues, PRs, and applying personality.
tests/test_github_issues.py: New test file for the `GitHubIssueClient` class in `aider/github_issues.py`, covering basic API interactions and error handling.