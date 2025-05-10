from pathlib import Path
from typing import Optional
import logging
from pydantic import Field

from src.models.problem import Problem
from src.config.yaml_object import YamlObject
from src.utils.io_utils import clone_repo


class Environment(YamlObject):
    instance_id: str = Field(..., description="Unique identifier for this workflow instance.")
    root_path: Path = Field(..., description="Path to the root directory of the robot_swe project.")
    root_output: Path = Field(..., description="Path to the root directory where all instance outputs are stored.")
    repo_path: Optional[Path] = Field(None, description="Path to the cloned target repository.")
    output_path: Optional[Path] = Field(None, description="Path to the output directory for the current workflow instance.")
    problem: Optional[Problem] = Field(None, description="Problem object that describes the issue to be solved.")

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger("rich")

    def load_problem(self, problem: Problem) -> None:
        """
        Clone the problem repo and initialize paths.
        """
        self.problem = problem
        self.output_path = self.root_output / self.instance_id
        self.output_path.mkdir(parents=True, exist_ok=True)

        self.repo_path = clone_repo(
            instance_id=problem.instance_id,
            repo=problem.repo,
            base_commit=problem.base_commit,
            target_folder=self.root_output / "repos",
            logger=self.logger,
        )
