"""GitHub issue parser for converting issues into structured problem definitions."""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class CodeReference:
    """Reference to code in an issue."""
    language: str
    content: str
    filename: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None

@dataclass
class ProblemDefinition:
    """Structured representation of a coding problem from an issue."""
    title: str
    description: str
    code_references: List[CodeReference]
    labels: List[str]
    success_criteria: List[str]
    context: Dict[str, str]
    issue_number: int
    issue_url: str

class IssueParser:
    """Parser for converting GitHub issues into structured problem definitions."""

    # Regex patterns for extracting information
    CODE_BLOCK_PATTERN = re.compile(
        r"```(\w+)?\n"  # Language (optional)
        r"(.*?)\n"      # Content
        r"```",         # End
        re.DOTALL
    )
    
    FILE_REF_PATTERN = re.compile(
        r"(?:in|at|file)[:\s]+(?:`)?([^`\n]+?)(?:`)?:"  # Filename
        r"(?:lines?\s+)?(\d+)(?:-(\d+))?"                # Line numbers (optional)
    )
    
    SUCCESS_MARKERS = [
        "success criteria",
        "definition of done",
        "acceptance criteria",
        "expected outcome",
        "expected result"
    ]

    def __init__(self):
        """Initialize the issue parser."""
        pass

    def _extract_code_blocks(self, content: str) -> List[CodeReference]:
        """Extract code blocks from markdown content.
        
        Args:
            content: Markdown content containing code blocks
            
        Returns:
            List of CodeReference objects
        """
        code_refs = []
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            language = match.group(1) or "text"
            code_content = match.group(2).strip()
            
            # Look for filename and line references before the code block
            content_before = content[:match.start()]
            lines = content_before.split('\n')
            file_ref = None
            
            # Check last few lines before code block for file references
            for line in lines[-3:]:
                file_match = self.FILE_REF_PATTERN.search(line)
                if file_match:
                    file_ref = file_match
                    break
            
            code_ref = CodeReference(
                language=language,
                content=code_content,
                filename=file_ref.group(1) if file_ref else None,
                start_line=int(file_ref.group(2)) if file_ref else None,
                end_line=int(file_ref.group(3)) if file_ref and file_ref.group(3) else None
            )
            code_refs.append(code_ref)
            
        return code_refs

    def _extract_success_criteria(self, content: str) -> List[str]:
        """Extract success criteria from issue content.
        
        Args:
            content: Issue content/description
            
        Returns:
            List of success criteria strings
        """
        criteria = []
        lines = content.lower().split('\n')
        
        # Find section with success criteria
        for i, line in enumerate(lines):
            if any(marker in line for marker in self.SUCCESS_MARKERS):
                # Collect bullet points that follow
                for next_line in lines[i+1:]:
                    next_line = next_line.strip()
                    if not next_line:
                        continue
                    if next_line.startswith(('- ', '* ', '• ')):
                        criteria.append(next_line[2:].strip())
                    elif criteria:  # Stop if we hit non-bullet text after criteria
                        break
                break
                
        return criteria

    def _extract_context(self, content: str, comments: List[Dict]) -> Dict[str, str]:
        """Extract relevant context from issue content and comments.
        
        Args:
            content: Issue content/description
            comments: List of issue comments
            
        Returns:
            Dictionary of context information
        """
        context = {}
        
        # Add relevant sections from description
        sections = content.split('\n\n')
        for section in sections:
            if section.lower().startswith(('context:', 'background:', 'current behavior:')):
                key = section.split(':')[0].strip().lower()
                value = section.split(':', 1)[1].strip()
                context[key] = value
                
        # Add relevant information from comments
        for comment in comments:
            comment_body = comment['body']
            if any(marker in comment_body.lower() 
                  for marker in ['additional context', 'more details', 'to clarify']):
                context['additional_info'] = context.get('additional_info', '') + '\n' + comment_body
                
        return context

    def parse_issue(
        self,
        issue: Dict,
        comments: Optional[List[Dict]] = None
    ) -> ProblemDefinition:
        """Parse a GitHub issue into a structured problem definition.
        
        Args:
            issue: GitHub issue dictionary
            comments: Optional list of issue comments
            
        Returns:
            ProblemDefinition object
        """
        comments = comments or []
        content = issue['body'] or ''
        
        # Extract components
        code_refs = self._extract_code_blocks(content)
        success_criteria = self._extract_success_criteria(content)
        context = self._extract_context(content, comments)
        
        # Create problem definition
        return ProblemDefinition(
            title=issue['title'],
            description=content,
            code_references=code_refs,
            labels=[label['name'] for label in issue['labels']],
            success_criteria=success_criteria,
            context=context,
            issue_number=issue['number'],
            issue_url=issue['html_url']
        )
