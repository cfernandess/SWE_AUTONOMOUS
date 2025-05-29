import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from smolagents.tools import Tool

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem


class PatchValidatorTool(Tool):
    name = "patch_validator_tool"
    description = (
        "Validate a unified diff patch string using Ruff.\n\n"
        "Returns a JSON string in one of the following formats:\n"
        '{ "status": "PASSED", "cleaned_patch": "<patch>" }\n'
        "or\n"
        '{ "status": "ERROR", "error_message": "<message>" }'
    )

    inputs = {
        "input": {
            "type": "string",
            "description": "A single unified diff string, possibly spanning multiple files.",
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
        self.repo_path = self.environment.repo_path
        self.ruff_bin = shutil.which("ruff") or "ruff"

    def forward(self, input: str) -> str:
        try:
            chunks = self._extract_chunks(input)
            fixed_diffs = []

            for chunk in chunks:
                path = chunk["path"]
                original_diff = chunk["diff"]

                patched_text, fixed_text = self._apply_patch(path, original_diff)

                # Log intermediate patch/fix outputs
                self.logger.debug(
                    f"[PatchValidatorTool] Patched text for {path}:\n{patched_text}"
                )
                self.logger.debug(
                    f"[PatchValidatorTool] Fixed text for {path}:\n{fixed_text}"
                )

                unified_diff = self._generate_diff(path, patched_text, fixed_text)
                self.logger.debug(
                    f"[PatchValidatorTool] Unified diff for {path}:\n{unified_diff}"
                )

                fixed_diffs.append(unified_diff)

            output = "\n".join(diff for diff in fixed_diffs if diff.strip())
            cleaned_patch = output if output.strip() else input

            self.logger.info(f"[PatchValidatorTool] Cleaned patch:\n{cleaned_patch}")

            return json.dumps(
                {
                    "status": "PASSED",
                    "cleaned_patch": cleaned_patch,
                }
            )

        except Exception as e:
            self.logger.error(f"[PatchValidatorTool] Exception during validation: {e}")
            return json.dumps(
                {
                    "status": "ERROR",
                    "error_message": f"{type(e).__name__}: {e}",
                }
            )

    def _extract_chunks(self, patch: str) -> List[dict]:
        parts = re.split(r"^diff --git a/(.+?) b/\1\n", patch, flags=re.MULTILINE)
        return [
            {
                "path": parts[i],
                "diff": f"diff --git a/{parts[i]} b/{parts[i]}\n{parts[i+1]}",
            }
            for i in range(1, len(parts), 2)
        ]

    def _apply_patch(self, path: str, diff: str) -> tuple[str, str]:
        file_path = self.repo_path / path
        original = "" if "@@ -0,0 +" in diff else file_path.read_text()
        from src.utils.io_utils import apply_patch_to_file

        patched_text = apply_patch_to_file(original, diff, Path(path).name)

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tmp:
            tmp.write(patched_text)
            tmp.flush()

            subprocess.run(
                [self.ruff_bin, "check", "--fix", tmp.name],
                capture_output=True,
                text=True,
            )

            tmp.seek(0)
            fixed_text = tmp.read()
            Path(tmp.name).unlink(missing_ok=True)

        return patched_text, fixed_text

    def _generate_diff(self, path: str, before: str, after: str) -> str:
        import difflib

        return "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
