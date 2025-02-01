"""Tests for problem generator."""

import pytest
from aider.issue_parser import ProblemDefinition, CodeReference
from aider.problem_generator import ProblemGenerator, AiderProblem

# Test data
@pytest.fixture
def sample_problem():
    """Create a sample problem definition."""
    return ProblemDefinition(
        title="Implement feature X",
        description="We need to implement feature X for better performance",
        code_references=[
            CodeReference(
                language="python",
                content="def test():\n    pass",
                filename="test.py",
                start_line=10,
                end_line=15
            ),
            CodeReference(
                language="python",
                content="def another():\n    return True",
                filename="test.py",
                start_line=20,
                end_line=25
            ),
            CodeReference(
                language="javascript",
                content="function test() { }",
                filename="main.js",
                start_line=5
            )
        ],
        labels=["enhancement", "priority-high"],
        success_criteria=[
            "Feature X works correctly",
            "All tests pass",
            "Performance improved"
        ],
        context={
            "context": "This is important background",
            "current behavior": "Currently not implemented",
            "additional_info": "Extra details here"
        },
        issue_number=123,
        issue_url="https://github.com/owner/repo/issues/123"
    )

@pytest.fixture
def generator():
    """Create a ProblemGenerator instance."""
    return ProblemGenerator()

def test_build_task_description(generator, sample_problem):
    """Test building task description."""
    task = generator._build_task_description(sample_problem)
    
    assert sample_problem.title in task
    assert "Background:" in task
    assert "Current Behavior:" in task
    assert "Additional Information:" in task
    assert "This is important background" in task
    assert "Currently not implemented" in task
    assert "Extra details here" in task

def test_collect_file_references(generator, sample_problem):
    """Test collecting file references."""
    files = generator._collect_file_references(sample_problem)
    
    assert len(files) == 2
    assert "test.py" in files
    assert "main.js" in files

def test_organize_code_references(generator, sample_problem):
    """Test organizing code references."""
    code_by_file = generator._organize_code_references(sample_problem)
    
    assert len(code_by_file) == 2
    assert "test.py" in code_by_file
    assert "main.js" in code_by_file
    
    # Check test.py contents
    test_py_content = code_by_file["test.py"]
    assert "Lines 10-15" in test_py_content
    assert "Lines 20-25" in test_py_content
    assert "def test():" in test_py_content
    assert "def another():" in test_py_content
    
    # Check main.js contents
    main_js_content = code_by_file["main.js"]
    assert "Lines 5" in main_js_content
    assert "function test()" in main_js_content

def test_build_context_string(generator, sample_problem):
    """Test building context string."""
    code_by_file = generator._organize_code_references(sample_problem)
    context = generator._build_context_string(sample_problem, code_by_file)
    
    assert "Issue Labels: " in context
    assert "enhancement" in context
    assert "priority-high" in context
    
    assert "Relevant Files:" in context
    assert "test.py" in context
    assert "main.js" in context
    
    assert "Success Criteria:" in context
    assert "Feature X works correctly" in context
    assert "All tests pass" in context
    assert "Performance improved" in context

def test_generate_problem(generator, sample_problem):
    """Test complete problem generation."""
    result = generator.generate_problem(sample_problem)
    
    assert isinstance(result, AiderProblem)
    assert sample_problem.title in result.task
    assert len(result.files_to_modify) == 2
    assert len(result.acceptance_criteria) == 3
    assert len(result.related_code) == 2
    assert result.metadata["issue_number"] == 123
    assert result.metadata["issue_url"] == sample_problem.issue_url
    assert len(result.metadata["labels"]) == 2

def test_generate_problem_with_additional_context(generator, sample_problem):
    """Test problem generation with additional context."""
    additional_context = {
        "repository": "owner/repo",
        "branch": "feature-x"
    }
    
    result = generator.generate_problem(sample_problem, additional_context)
    
    assert result.metadata["repository"] == "owner/repo"
    assert result.metadata["branch"] == "feature-x"

def test_generate_problem_minimal(generator):
    """Test generating problem from minimal definition."""
    minimal_problem = ProblemDefinition(
        title="Simple task",
        description="Just do it",
        code_references=[],
        labels=[],
        success_criteria=[],
        context={},
        issue_number=456,
        issue_url="https://github.com/owner/repo/issues/456"
    )
    
    result = generator.generate_problem(minimal_problem)
    
    assert isinstance(result, AiderProblem)
    assert result.task == "Simple task"
    assert len(result.files_to_modify) == 0
    assert len(result.acceptance_criteria) == 0
    assert len(result.related_code) == 0
    assert result.metadata["issue_number"] == 456
