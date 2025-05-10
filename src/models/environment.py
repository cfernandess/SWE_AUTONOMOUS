# environment.py
from pathlib import Path
from typing import Optional

from pydantic import Field


from src.models.problem import Problem
from src.config.yaml_object import YamlObject


class Environment(YamlObject):
    """
    Base class for environment settings shared across all steps.
    Automatically configures per-step config/output/log directories and manages repository access.
    Sets up:
    - Root outputs directory.
    - Per-phase subdirectories.
    - Per-step subdirectories (LOCATIONS, GENERATE).
    """

    instance_id: str = Field(
        ..., description="Unique identifier for this workflow instance."
    )
    root_path: Path = Field(
        ..., description="Path to the root directory of the robot_swe project."
    )
    root_output: Path = Field(
        ...,
        description="Path to the root directory where all instance outputs are stored.",
    )
    repo_path: Optional[Path] = Field(
        None, description="Path to the cloned target repository."
    )
    output_path: Optional[Path] = Field(
        None,
        description="Path to the output directory for the current workflow instance.",
    )
    problem: Optional[Problem] = Field(
        None, description="Problem object that describes the issue to be solved."
    )

    def __init__(self, **data) -> None:
        super().__init__(**data)

# EOF
