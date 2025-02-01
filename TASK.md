# GitHub Issues Integration for Aider

This project extends aider to automatically process and work with GitHub issues as problem definitions.

## Tasks

### 1. Create GitHub Issue Integration Module 
- [x] Create `github_issues.py` module
- [x] Implement GitHub API authentication handling
- [x] Add issue fetching functionality (by repo, labels, status)
- [x] Add rate limiting and pagination handling
- [x] Write tests for GitHub API integration

### 2. Develop Issue Parser 
- [x] Create issue content parser
- [x] Extract code snippets and context
- [x] Parse issue labels and metadata
- [x] Handle issue comments and discussion threads
- [x] Add support for issue templates
- [x] Write tests for parser functionality

### 3. Build Problem Definition Generator 
- [x] Define problem definition schema
- [x] Create converter from GitHub issue to problem definition
- [x] Handle different issue formats and templates
- [x] Add validation for generated definitions
- [x] Write tests for definition generation

### 4. Integrate with Aider Core 
- [x] Add CLI commands for GitHub issue processing
- [x] Implement issue-to-aider workflow
- [x] Add configuration options for GitHub integration
- [x] Create documentation for GitHub features
- [x] Write integration tests

### 5. Add Issue Update Features
- [ ] Implement progress tracking
- [ ] Add solution posting capability
- [ ] Handle issue status updates
- [ ] Add comment management
- [ ] Write tests for update features

## Progress

### Completed
1. **GitHub Issue Integration Module** (`github_issues.py`)
   - Created GitHubIssueClient for API interaction
   - Implemented issue and comment fetching
   - Added rate limit handling and configuration
   - Added repository URL parsing
   - Added token configuration via env var or direct input

2. **Issue Parser** (`issue_parser.py`)
   - Created structured problem definition format
   - Implemented code block extraction
   - Added success criteria parsing
   - Added context extraction from comments

3. **Problem Generator** (`problem_generator.py`)
   - Implemented conversion to Aider format
   - Added task description building
   - Added file reference collection
   - Added code reference organization

4. **Command Integration** (`commands.py`)
   - Added `/issue` command to process individual issues
     - Supports owner/repo#number format
     - Supports full GitHub issue URLs
   - Added `/issues` command to list repository issues
     - Shows issue numbers, titles, and labels
     - Supports repository name and URL formats

### In Progress
1. **Testing**
   - [x] Complete test coverage for new commands
   - [x] Add integration tests
   - [x] Add token configuration tests
   - [x] Add rate limit tests

2. **Documentation**
   - [ ] Add user documentation for new commands
   - [ ] Add developer documentation for new modules

### To Do
1. **Configuration**
   - [x] Add GitHub token configuration
   - [x] Add rate limit settings
   - [x] Add configuration file support

2. **Features**
   - [ ] Add issue comment support
   - [ ] Add issue update support
   - [ ] Add issue creation support

3. **Integration**
   - [ ] Add automatic issue updates with progress
   - [ ] Add comment management
   - [ ] Add file change tracking

## Dependencies
- requests: HTTP client for GitHub API
- pytest: Testing framework
- responses: HTTP mocking for tests

## Notes
- All code changes follow minimal and concise design principles
- Focus on maintainability and readability
- Error handling with user-friendly messages
- Token configuration via GITHUB_TOKEN environment variable
- Rate limit handling with automatic tracking
