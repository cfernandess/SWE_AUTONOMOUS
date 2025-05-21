# bash_tool.py
import shlex
import subprocess  # nosec B603
from datetime import datetime, UTC
from time import perf_counter

from smolagents.tools import Tool

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem


class BashTool(Tool):
    name = "bash"
    description = """Run commands in a bash shell.\n
* State is persistent across command calls and discussions with the user.\n
* You can use sed to inspect file ranges, e.g., 'sed -n 10,25p /path/file.py'.\n
* Long outputs may be truncated.\n
* You can use `ruff` directly to lint or fix Python files — e.g., `ruff check file.py` or `ruff check --fix file.py`.\n
* This is the preferred way to perform linting and auto-fixing of code.\n
"""
    inputs = {
        "command": {
            "type": "string",
            "description": "The bash command to run (single line, no pipes or redirects).",
        }
    }
    output_type = "string"

    def __init__(
        self,
        problem: Problem,
        environment: Environment,
        config_agent: ConfigAgent,
    ):
        super().__init__()
        self.problem = problem
        self.environment = environment
        self.logger = environment.logger
        self.traj_logger = environment.traj_logger
        self.config_agent = config_agent

    def forward(self, command: str) -> str:
        if self.traj_logger:
            self.traj_logger.log(
                step_type="tool_call",
                tool=self.name,
                content={"command": command},
                metadata={"timestamp": datetime.now(UTC).isoformat()},
            )

        start = perf_counter()

        stdout = ""
        stderr = ""
        error = ""
        try:
            command_list = shlex.split(command)
            result = subprocess.run(
                command_list, capture_output=True, text=True, timeout=30
            )  # nosec B603
            stdout = result.stdout
            stderr = result.stderr
        except subprocess.TimeoutExpired:
            error = "Command timed out after 30 seconds"
        except Exception as e:
            error = str(e)

        output = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nERROR:\n{error}"

        if self.traj_logger:
            self.traj_logger.log(
                step_type="tool_return",
                tool=self.name,
                content=output,
                metadata={
                    "timestamp": datetime.now(UTC).isoformat(),
                    "duration_seconds": perf_counter() - start,
                },
            )

        return output


# EOF
