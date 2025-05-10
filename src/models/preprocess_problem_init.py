# preprocess_problem_init.py
from typing import List

from pydantic import Field

from src.models.jasonl_object import JsonlObject


class PreprocessProblemInit(JsonlObject):
    """
    Represents the initial output of the preprocessing phase.

    Includes semantic search queries (code/docs), environment metadata
    (Python version, test framework), and retrieved file locations.
    """

    query_code: List[str] = Field(
        default_factory=list,
        description="List of semantic search queries over the repository code segments to retrieve relevant Python code segments.",
    )
    query_doc: List[str] = Field(
        default_factory=list,
        description="List of semantic search queries over the repository documentation segments to retrieve relevant insights.",
    )
    python_version: str = Field(
        "3.6", description="The Python execution environment version."
    )
    test_framework: str = Field(
        "pytest",
        description="Testing style or framework used (e.g., pytest, unittest).",
    )
    preprocess_problem_statement: str = Field(
        "N/A",
        description="Reformulated problem statement with a solution-oriented focus.",
    )

# EOF
