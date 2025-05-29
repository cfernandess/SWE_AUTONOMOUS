# bash_tool.py
import shlex
import subprocess  # nosec B603
from time import perf_counter

from smolagents.tools import Tool

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem


class BashTool(Tool):
    name = "bash"
    description = """Run commands in a bash shell.\n
* Commands are executed from the repository root.\n
* Use `grep`, `sed`, `find`, or `ruff` to inspect and lint files.\n
* You can view file content ranges using: `sed -n 10,25p file.py`.\n
* Output may be truncated. Avoid commands that span multiple files.\n
"""

    inputs = {
        "command": {
            "type": "string",
            "description": "The bash command to run (no pipes, no redirects).",
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
        self.config_agent = config_agent
        self.logger = environment.logger
        self.traj_logger = environment.traj_logger
        self.MAX_OUTPUT_CHARS = getattr(config_agent, "max_tool_output_chars", 10_000)

    def forward(self, command: str) -> str:
        start = perf_counter()
        stdout = ""
        stderr = ""
        error = ""
        result = None
        working_dir = self.environment.repo_path

        try:
            command_list = shlex.split(command)
            print(f"[BashTool] Running: {' '.join(command_list)}")
            print(f"[BashTool] CWD: {working_dir}")

            result = subprocess.run(
                command_list,
                capture_output=True,
                timeout=30,
                cwd=str(working_dir),
            )

            try:
                stdout = result.stdout.decode("utf-8")
            except UnicodeDecodeError:
                stdout = result.stdout.decode("utf-8", errors="ignore")

            try:
                stderr = result.stderr.decode("utf-8")
            except UnicodeDecodeError:
                stderr = result.stderr.decode("utf-8", errors="ignore")

        except subprocess.TimeoutExpired:
            error = "Command timed out after 30 seconds"
        except Exception as e:
            error = str(e)

        output = f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}\nERROR:\n{error}"

        was_truncated = False
        if len(output) > self.MAX_OUTPUT_CHARS:
            was_truncated = True
            output = output[: self.MAX_OUTPUT_CHARS].rstrip()
            output += (
                "\n\n⚠️ Output truncated due to tool output limits "
                f"({self.MAX_OUTPUT_CHARS} chars max). Please refine your command.\n"
            )

        if self.traj_logger:
            self.traj_logger.log_step(
                response="",
                thought="Run shell command in project root.",
                action=f"bash: {command}",
                observation=output,
                query=[{"role": "user", "content": command}],
                state={
                    "repo_path": str(self.environment.repo_path),
                    "working_dir": str(working_dir),
                    "exit_code": result.returncode if result else -1,
                    "duration_seconds": perf_counter() - start,
                    "truncated": was_truncated,
                },
            )

        return output


# EOF
