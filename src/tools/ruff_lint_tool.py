# ruff_lint_tool.py
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from time import perf_counter

from smolagents.tools import Tool

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.utils.io_utils import apply_patch_to_file


class RuffLintTool(Tool):
    name = "ruff_lint_tool"
    description = (
        "Checks Python patches using Ruff.\n"
        "\n"
        "This tool applies a patch to a temporary Python file and runs `ruff check`.\n"
        "\n"
        "- Returns 'PASSED' if all patches succeed.\n"
        "- Returns 'ERROR: <reason>' if any patch fails.\n"
        "\n"
        "Only one string is returned. If any patch fails, the tool stops and returns the error message.\n"
    )

    inputs = {
        "input": {
            "type": "array",
            "description": "List of patches with path and unified diff.",
            "items": {
                "type": "object",
                "properties": {"diff": {"type": "string"}, "path": {"type": "string"}},
                "required": ["diff", "path"],
            },
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
        self.ruff_bin = shutil.which("ruff") or "ruff"
        self.repo_path = self.environment.repo_path

    def forward(self, input: list) -> str:
        start = perf_counter()

        for solution in input:
            if (
                not isinstance(solution, dict)
                or "path" not in solution
                or "diff" not in solution
            ):
                result = "ERROR: Invalid input format. Each item must contain 'path' and 'diff'."
                break

            result = self._process_single_solution(solution)
            if result != "PASSED":
                break
        else:
            result = "PASSED"

        if self.traj_logger:
            self.traj_logger.log_step(
                response="",
                thought="Run Ruff linter to validate patch formatting and syntax.",
                action=f"{self.name}: check",
                observation=result,
                query=input,
                state={
                    "repo_path": str(self.repo_path),
                    "num_patches": len(input),
                    "ruff_bin": self.ruff_bin,
                    "duration_seconds": perf_counter() - start,
                },
            )

        return result

    def _process_single_solution(self, solution: dict) -> str:
        path_str = solution["path"]
        diff = self.fix_hunk_headers(solution["diff"])
        file_path = self.repo_path / path_str
        is_new_file = "@@ -0,0 +" in diff

        try:
            original_text = "" if is_new_file else file_path.read_text()
            patched_text = apply_patch_to_file(original_text, diff, Path(path_str).name)
        except Exception as e:
            return (
                f"Patch failed for path: {path_str}\n\n"
                f"Error: {type(e).__name__}: {e}"
            )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(patched_text)
            tmp.flush()
            tmp_path = Path(tmp.name)

        check = subprocess.run(
            [self.ruff_bin, "check", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        tmp_path.unlink(missing_ok=True)

        if check.returncode == 0:
            return "PASSED"
        else:
            error_output = check.stderr.strip() or check.stdout.strip()
            return (
                f"Lint failed for patch on path: {path_str}\n\n"
                f"Ruff output:\n{error_output}"
            )

    @staticmethod
    def fix_hunk_headers(diff: str) -> str:
        """
        Fix unified diff hunk headers to match actual line counts.
        """
        hunk_re = re.compile(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@")
        lines = diff.splitlines(keepends=True)
        fixed_lines = []
        i = 0

        while i < len(lines):
            line = lines[i]
            match = hunk_re.match(line)
            if match:
                start_i = i
                orig_start, _, new_start, _ = map(lambda x: int(x or 0), match.groups())
                i += 1
                minus_count = plus_count = 0
                while i < len(lines) and not lines[i].startswith("@@"):
                    if lines[i].startswith("-") and not lines[i].startswith("---"):
                        minus_count += 1
                    elif lines[i].startswith("+") and not lines[i].startswith("+++"):
                        plus_count += 1
                    i += 1

                new_header = (
                    f"@@ -{orig_start},{minus_count} +{new_start},{plus_count} @@\n"
                )
                fixed_lines.append(new_header)
                fixed_lines.extend(lines[start_i + 1 : i])
            else:
                fixed_lines.append(line)
                i += 1

        return "".join(fixed_lines)


# EOF
