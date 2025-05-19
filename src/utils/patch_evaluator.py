# patch_evaluator.py
import json
import re
import subprocess
from enum import Enum
from typing import Dict, Tuple

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.utils.docker_utils import setup_repo, run_command, apply_diff
from src.utils.test_framework_utils import TestFrameworkUtils


class TestFramework(str, Enum):
    PYTEST = "pytest"
    UNITTEST = "unittest"
    TOX = "tox"
    NO_TESTS = "none"


class PatchEvaluator:
    def __init__(
        self,
        problem: Problem,
        environment: Environment,
        config_agent: ConfigAgent,
    ):
        self.problem = problem
        self.environment = environment
        self.config_agent = config_agent
        self.repo_path = self.environment.repo_path
        self.base_commit = self.problem.base_commit
        self.logger = self.environment.logger

        # instantiate lint tool once

    import re

    @staticmethod
    def extract_file_path_from_diff(diff_text: str) -> str:
        """
        Extracts the target file path from the first `+++ b/...` line in a unified diff.
        Returns None if no such line exists.
        """
        match = re.search(r'^\+\+\+ b/(.+)', diff_text, re.MULTILINE)
        return match.group(1) if match else None

    def run_tests(self, test_cmd: str) -> (str, int):
        if not test_cmd:
            return "[SKIPPED] No test command specified", -1
        return run_command(test_cmd, cwd=self.repo_path)

    def evaluate(self, solution_patch: str) -> Dict:
        setup_repo(self.repo_path, self.base_commit)

        # 1. Load patch JSON
        try:
            patch_obj = json.loads(solution_patch)
            diff = patch_obj["diff"]
            path_str = self.extract_file_path_from_diff(diff)
        except Exception as e:
            return {
                "type": "invalid_patch_format",
                "output": f"ERROR: Could not parse patch JSON - {e}"
            }

        self.logger.info(f"[PatchEvaluator] 🧩 Applying patch to file: {path_str}")
        file_path = self.repo_path / path_str
        is_new_file = "@@ -0,0 +" in diff

        try:
            original_text = "" if is_new_file else file_path.read_text()
            patched_text, code = apply_diff(diff, self.repo_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(patched_text)
        except Exception as e:
            return {
                "type": "apply_patch_failed",
                "output": f"Patch application error: {e}",
            }

        self.logger.info("[PatchEvaluator] 🧹 Running Ruff lint check...")
        passed, lint_result = self.run_ruff_lint_and_fix()
        if not passed:
            return {
                "type": "ruff_lint_failed",
                "output": lint_result,
            }

        self.logger.info(f"[PatchEvaluator] 🧪 Running tests (Ruff: {lint_result})...")
        test_cmd = TestFrameworkUtils.get_test_command(
            TestFrameworkUtils.detect_test_framework(self.repo_path)
        )
        test_out, test_code = self.run_tests(test_cmd)

        return {
            "type": "existing_tests",
            "exit_code": test_code,
            "output": test_out,
            "lint_status": lint_result,
        }

    def run_ruff_lint_and_fix(self) -> Tuple[bool, str]:
        """Run Ruff linter, fix if needed, and confirm no remaining errors."""

        def _run_ruff(fix: bool = False) -> Tuple[int, str]:
            args = ["ruff", "check"]
            if fix:
                args.append("--fix")
            proc = subprocess.run(
                args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
            )
            output = proc.stdout + proc.stderr
            return proc.returncode, output.strip()

        code, out = _run_ruff(fix=False)
        if code == 0:
            return True, "PASSED"

        self.logger.warning("[Ruff] ❌ Initial Ruff check failed. Attempting auto-fix...")
        fix_code, fix_out = _run_ruff(fix=True)
        if fix_code != 0:
            return False, f"ERROR after --fix:\n{fix_out}"

        # Final confirmation pass
        confirm_code, confirm_out = _run_ruff(fix=False)
        if confirm_code == 0:
            self.logger.info("[Ruff] ✅ Auto-fix succeeded.")
            return True, "PASSED: AUTO-FIX - SUCCEEDED"
        else:
            return False, f"ERROR after fix: {confirm_out}"

# EOF
