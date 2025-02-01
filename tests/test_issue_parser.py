"""Tests for GitHub issue parser."""

import pytest
from aider.issue_parser import IssueParser, CodeReference, ProblemDefinition

# Test data
MOCK_ISSUE = {
    "number": 123,
    "title": "Add feature X",
    "body": """We need to implement feature X.

Context:
This is important for improving performance.

```python
def example():
    pass
```

In file.py:10-15:
```python
def another_example():
    return True
```

Success Criteria:
- Feature X works correctly
- All tests pass
- Performance improved by 20%
""",
    "html_url": "https://github.com/owner/repo/issues/123",
    "labels": [
        {"name": "enhancement"},
        {"name": "priority-high"}
    ]
}

MOCK_COMMENTS = [
    {
        "body": "Additional context: Feature X should handle edge cases."
    },
    {
        "body": "Just a regular comment."
    }
]

@pytest.fixture
def parser():
    """Create an IssueParser instance."""
    return IssueParser()

def test_extract_code_blocks_simple(parser):
    """Test extracting code blocks without file references."""
    content = '''
Here's some code:
```python
def test():
    pass
```
    '''
    refs = parser._extract_code_blocks(content)
    assert len(refs) == 1
    assert refs[0].language == "python"
    assert "def test():" in refs[0].content
    assert refs[0].filename is None

def test_extract_code_blocks_with_file_ref(parser):
    """Test extracting code blocks with file references."""
    content = '''
In file.py:10-15:
```python
def test():
    pass
```
    '''
    refs = parser._extract_code_blocks(content)
    assert len(refs) == 1
    assert refs[0].filename == "file.py"
    assert refs[0].start_line == 10
    assert refs[0].end_line == 15

def test_extract_code_blocks_multiple_formats(parser):
    """Test different file reference formats."""
    test_cases = [
        "in file.py:10:",
        "at file.py:10-15:",
        "file: file.py:10:",
        "in `file.py`:10-15:"
    ]
    
    for case in test_cases:
        content = f'''{case}
```python
def test():
    pass
```'''
        refs = parser._extract_code_blocks(content)
        assert len(refs) == 1
        assert refs[0].filename == "file.py"
        assert refs[0].start_line is not None

def test_extract_success_criteria_bullet_points(parser):
    """Test extracting success criteria with different bullet point styles."""
    content = '''
Success Criteria:
- First criteria
* Second criteria
• Third criteria
'''
    criteria = parser._extract_success_criteria(content)
    assert len(criteria) == 3
    assert "First criteria" in criteria
    assert "Second criteria" in criteria
    assert "Third criteria" in criteria

def test_extract_success_criteria_different_headers(parser):
    """Test different success criteria section headers."""
    headers = [
        "Success Criteria:",
        "Definition of Done:",
        "Acceptance Criteria:",
        "Expected Outcome:",
        "Expected Result:"
    ]
    
    for header in headers:
        content = f'''{header}
- Test criteria'''
        criteria = parser._extract_success_criteria(content)
        assert len(criteria) == 1
        assert "Test criteria" in criteria

def test_extract_context(parser):
    """Test extracting context from issue and comments."""
    content = '''
Context:
Important background info.

Current Behavior:
Not working properly.
'''
    comments = [
        {"body": "Additional context: More details here."},
        {"body": "Not relevant."},
        {"body": "To clarify: Extra info."}
    ]
    
    context = parser._extract_context(content, comments)
    assert "context" in context
    assert "current behavior" in context
    assert "additional_info" in context
    assert "More details" in context["additional_info"]
    assert "Extra info" in context["additional_info"]

def test_parse_issue_complete(parser):
    """Test complete issue parsing with all components."""
    result = parser.parse_issue(MOCK_ISSUE, MOCK_COMMENTS)
    
    assert isinstance(result, ProblemDefinition)
    assert result.title == "Add feature X"
    assert result.issue_number == 123
    assert len(result.code_references) == 2
    assert len(result.labels) == 2
    assert "enhancement" in result.labels
    assert len(result.success_criteria) == 3
    assert "Feature X works correctly" in result.success_criteria
    assert "context" in result.context
    assert "additional_info" in result.context

def test_parse_issue_minimal(parser):
    """Test parsing issue with minimal content."""
    minimal_issue = {
        "number": 456,
        "title": "Simple issue",
        "body": "Just a description",
        "html_url": "https://github.com/owner/repo/issues/456",
        "labels": []
    }
    
    result = parser.parse_issue(minimal_issue)
    
    assert isinstance(result, ProblemDefinition)
    assert result.title == "Simple issue"
    assert result.description == "Just a description"
    assert len(result.code_references) == 0
    assert len(result.labels) == 0
    assert len(result.success_criteria) == 0
    assert isinstance(result.context, dict)

def test_parse_issue_empty_body(parser):
    """Test parsing issue with empty body."""
    empty_issue = {
        "number": 789,
        "title": "Empty issue",
        "body": None,
        "html_url": "https://github.com/owner/repo/issues/789",
        "labels": []
    }
    
    result = parser.parse_issue(empty_issue)
    
    assert isinstance(result, ProblemDefinition)
    assert result.title == "Empty issue"
    assert result.description == ""
    assert len(result.code_references) == 0
