# preprocess_problem.py
from pathlib import Path
from typing import List, Annotated, Optional

from pydantic import Field, StringConstraints

from src.models.jasonl_object import JsonlObject
from src.models.preprocess_problem_init import PreprocessProblemInit
from src.models.problem import Problem

FileExtStr = Annotated[str, StringConstraints(pattern=r"^\.[a-zA-Z0-9\+\-]+$")]


class PreprocessProblem(JsonlObject):
    """
    Formats a Problem into an LLM-friendly prompt.

    Includes repository metadata (structure, files), preprocessing outputs
    for solution and test orientations, and indexing settings.
    """

    problem: Problem = Field(..., description="The original problem instance.")
    repo_path: Optional[Path] = Field(
        None, description="Path to the cloned target repository."
    )
    repo_structure: str = Field(
        "N/A", description="Formatted repository structure for LLM."
    )
    repo_files: List[Path] = Field(
        default_factory=list,
        description="List of files collected during repo traversal.",
    )
    doc_file_ext: List[FileExtStr] = Field(
        [".md", ".txt", ".yaml", ".rst"], description="Document file extensions."
    )
    code_file_ext: List[FileExtStr] = Field(
        [".py"], description="Code file extensions."
    )
    test: PreprocessProblemInit = Field(
        None, description="Preprocessing output (test orientation)."
    )
    solution: PreprocessProblemInit = Field(
        None, description="Preprocessing output (solution orientation)."
    )


# EOF
