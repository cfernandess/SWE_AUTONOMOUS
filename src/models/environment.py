# environment.py
import logging
from pathlib import Path

from pydantic import Field, PrivateAttr
from rich.logging import RichHandler

from src.config.yaml_object import YamlObject
from src.models.problem import Problem
from src.utils.io_utils import clone_repo
from src.utils.trajectory_logger import TrajectoryLogger

# Set up global terminal logging with Rich
logging.basicConfig(
    level=logging.INFO, format="%(message)s", handlers=[RichHandler()], force=True
)


class Environment(YamlObject):
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
    repo_path: Path = Field(..., description="Path to the cloned target repository.")
    output_path: Path = Field(
        ...,
        description="Path to the output directory for the current workflow instance.",
    )
    swebench_path: Path = Field(
        Path("/Users/coby/PycharmProjects/SWE-bench"),
        description="Path to the SWE-bench.",
    )
    problem: Problem = Field(
        ..., description="Problem object that describes the issue to be solved."
    )
    _traj_logger: TrajectoryLogger = PrivateAttr()

    def __init__(self, root_path: Path, root_output: Path, problem: Problem):
        # Set fields manually via __setattr__ to bypass Pydantic validation in __init__
        super().__init__(
            instance_id=problem.instance_id,
            root_path=root_path,
            root_output=root_output,
            problem=problem,
            output_path=root_output / "outputs" / problem.instance_id,
            repo_path=Path(),  # placeholder, set below
        )
        self._traj_logger = TrajectoryLogger()
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Add file logging to output_path
        file_log_path = self.output_path / "log.txt"
        file_handler = logging.FileHandler(file_log_path, mode="w")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logging.getLogger().addHandler(file_handler)

        # Clone repo and set path
        self.repo_path = clone_repo(
            instance_id=problem.instance_id,
            repo=problem.repo,
            base_commit=problem.base_commit,
            target_folder=self.root_output / "repos",
            logger=self.logger,
        )

    @property
    def logger(self) -> logging.Logger:
        return logging.getLogger("rich")

    @property
    def traj_logger(self) -> TrajectoryLogger:
        return self._traj_logger


# EOF
