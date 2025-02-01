"""Convert structured problem definitions into aider-compatible format.

This module handles converting our ProblemDefinition objects into a format
that aider can understand and work with effectively.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

from .issue_parser import ProblemDefinition, CodeReference

@dataclass
class AiderProblem:
    """Aider-compatible problem representation."""
    task: str
    context: str
    files_to_modify: List[str]
    acceptance_criteria: List[str]
    related_code: Dict[str, str]
    metadata: Dict

class ProblemGenerator:
    """Generator for converting ProblemDefinition to aider-compatible format."""

    def _build_task_description(self, problem: ProblemDefinition) -> str:
        """Build a clear task description from the problem.
        
        Args:
            problem: Structured problem definition
            
        Returns:
            Task description string
        """
        # Start with the title and description
        task = f"{problem.title}\n\n"
        
        # Add relevant context sections
        if problem.context:
            for key, value in problem.context.items():
                if key in ['context', 'background']:
                    task += f"\nBackground:\n{value}\n"
                elif key == 'current behavior':
                    task += f"\nCurrent Behavior:\n{value}\n"
                elif key == 'additional_info':
                    task += f"\nAdditional Information:\n{value}\n"
        
        return task.strip()

    def _collect_file_references(self, problem: ProblemDefinition) -> List[str]:
        """Collect all referenced files from code blocks.
        
        Args:
            problem: Structured problem definition
            
        Returns:
            List of unique filenames
        """
        files = set()
        for ref in problem.code_references:
            if ref.filename:
                files.add(ref.filename)
        return sorted(list(files))

    def _organize_code_references(
        self,
        problem: ProblemDefinition
    ) -> Dict[str, str]:
        """Organize code references by file.
        
        Args:
            problem: Structured problem definition
            
        Returns:
            Dictionary mapping filenames to relevant code
        """
        code_by_file = {}
        
        # Group references by filename
        for ref in problem.code_references:
            if not ref.filename:
                continue
                
            if ref.filename not in code_by_file:
                code_by_file[ref.filename] = []
                
            location = ""
            if ref.start_line is not None:
                location = f"Lines {ref.start_line}"
                if ref.end_line:
                    location += f"-{ref.end_line}"
            
            code_block = f"{'=' * 40}\n"
            if location:
                code_block += f"Location: {location}\n"
            code_block += f"Language: {ref.language}\n\n"
            code_block += ref.content
            code_block += f"\n{'=' * 40}\n"
            
            code_by_file[ref.filename].append(code_block)
        
        # Join code blocks for each file
        return {
            filename: "\n\n".join(blocks)
            for filename, blocks in code_by_file.items()
        }

    def _build_context_string(
        self,
        problem: ProblemDefinition,
        code_by_file: Dict[str, str]
    ) -> str:
        """Build a comprehensive context string.
        
        Args:
            problem: Structured problem definition
            code_by_file: Organized code references
            
        Returns:
            Context string
        """
        context = []
        
        # Add label information
        if problem.labels:
            context.append("Issue Labels: " + ", ".join(problem.labels))
        
        # Add file references
        if code_by_file:
            context.append("\nRelevant Files:")
            for filename in sorted(code_by_file.keys()):
                context.append(f"- {filename}")
        
        # Add success criteria
        if problem.success_criteria:
            context.append("\nSuccess Criteria:")
            for criteria in problem.success_criteria:
                context.append(f"- {criteria}")
        
        return "\n".join(context)

    def generate_problem(
        self,
        problem: ProblemDefinition,
        additional_context: Optional[Dict] = None
    ) -> AiderProblem:
        """Generate an aider-compatible problem from a problem definition.
        
        Args:
            problem: Structured problem definition
            additional_context: Optional additional context to include
            
        Returns:
            AiderProblem instance
        """
        # Collect and organize information
        task = self._build_task_description(problem)
        files = self._collect_file_references(problem)
        code_by_file = self._organize_code_references(problem)
        context = self._build_context_string(problem, code_by_file)
        
        # Create metadata
        metadata = {
            "issue_number": problem.issue_number,
            "issue_url": problem.issue_url,
            "labels": [label for label in problem.labels]
        }
        if additional_context:
            metadata.update(additional_context)
        
        return AiderProblem(
            task=task,
            context=context,
            files_to_modify=files,
            acceptance_criteria=problem.success_criteria,
            related_code=code_by_file,
            metadata=metadata
        )
