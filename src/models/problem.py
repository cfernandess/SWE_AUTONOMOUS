# problem.py
import json
from typing import Annotated

from pydantic import Field, field_validator, BeforeValidator

from src.config.yaml_object import YamlObject


class Problem(YamlObject):
    """
    Represents a problem instance from the SWE-bench dataset.

    Includes metadata for repository, patches, and test outcomes (fail-to-pass, pass-to-pass).
    """

    instance_id: str = Field(..., description="Formatted ID: repo__name-PR-number.")
    problem_statement: str = Field(..., description="The issue title and body.")
    repo: str = Field(..., description="GitHub repository in owner/name format.")
    base_commit: str = Field(..., description="Commit hash before the solution PR.")
    created_at: str = Field("N/A", description="PR creation timestamp.")
    version: str = Field("N/A", description="Environment setup version.")

    hints_text: str = Field("N/A", description="Issue comments before solution PR.")
    environment_setup_commit: str = Field("N/A", description="Setup commit hash.")
    patch: str = Field("N/A", description="PR's non-test patch content.")
    test_patch: str = Field("N/A", description="PR's test-related patch.")
    fail_to_pass: Annotated[
        list[str], BeforeValidator(lambda v: json.loads(v) if isinstance(v, str) else v)
    ] = Field(
        default_factory=list, description="Tests that failed before and passed after."
    )
    pass_to_pass: Annotated[
        list[str], BeforeValidator(lambda v: json.loads(v) if isinstance(v, str) else v)
    ] = Field(default_factory=list, description="Tests that passed before and after.")
    model_config = {
        "frozen": True,
        "strict": False,  # ← allow coercion from str to Path
    }

    @classmethod
    @field_validator("fail_to_pass", "pass_to_pass", mode="before")
    def ensure_list_or_parse_json(cls, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        return value


# EOF
