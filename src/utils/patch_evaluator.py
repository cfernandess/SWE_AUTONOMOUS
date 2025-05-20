# patch_evaluator.py
import json
import re
import subprocess
from typing import Dict, Tuple

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.utils.docker_utils import setup_repo, run_command


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

    @staticmethod
    def extract_file_path_from_diff(diff_text: str) -> str:
        match = re.search(r'^\+\+\+ b/(.+)', diff_text, re.MULTILINE)
        return match.group(1) if match else None

    @staticmethod
    def normalize_nodeid(nodeid: str) -> str:
        return nodeid.replace("\\", "/").lstrip("./")

    def run_tests_and_check(self) -> Tuple[str, int, Dict[str, str]]:
        report_path = self.repo_path / ".pytest_results.json"
        test_cmd = [
            "pytest",
            "--json-report",
            f"--json-report-file={report_path}",
            "-q",
        ]
        out, code = run_command(test_cmd, cwd=self.repo_path)

        results = {}
        if report_path.exists():
            try:
                with report_path.open() as f:
                    report = json.load(f)
                    for test in report.get("tests", []):
                        norm = self.normalize_nodeid(test["nodeid"])
                        results[norm] = test["outcome"]
            except Exception as e:
                self.logger.warning(f"[PatchEvaluator] ⚠️ Failed to parse pytest JSON report: {e}")

        return out, code, results

    def apply_diff(self, diff_text: str) -> Tuple[bool, str]:
        diff_path = self.repo_path / "temp_patch.diff"
        diff_path.write_text(diff_text)

        result = subprocess.run(
            ["git", "apply", str(diff_path)],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        diff_path.unlink(missing_ok=True)

        if result.returncode != 0:
            return False, result.stderr.strip()

        return True, "Patch applied successfully"

    def evaluate(self, solution_patch: str) -> Dict:
        setup_repo(repo_path=self.repo_path, env_commit=self.problem.environment_setup_commit,
                   base_commit=self.problem.base_commit)

        try:
            patch_obj = json.loads(solution_patch)
            diff = patch_obj["diff"]
            path_str = self.extract_file_path_from_diff(diff)
            if path_str is None:
                raise ValueError("No valid file path found in diff")
        except Exception as e:
            return {
                "type": "invalid_patch_format",
                "output": f"ERROR: Could not parse patch JSON - {e}"
            }

        self.logger.info(f"[PatchEvaluator] 🧩 Applying patch to file: {path_str}")
        success, apply_msg = self.apply_diff(diff)
        if not success:
            return {
                "type": "apply_patch_failed",
                "output": f"Patch application error: {apply_msg}",
            }

        self.logger.info("[PatchEvaluator] 🧹 Running Ruff lint check...")
        passed, lint_result = self.run_ruff_lint_and_fix(path_str)
        if not passed:
            return {
                "type": "ruff_lint_failed",
                "output": lint_result,
            }

        fail_to_pass = json.loads(self.problem.fail_to_pass)
        pass_to_pass = json.loads(self.problem.pass_to_pass)
        tests_to_run = fail_to_pass + pass_to_pass

        self.logger.info(f"[PatchEvaluator] 🧪 Running tests: {tests_to_run}")
        test_out, test_code, test_results = self.run_tests_and_check()

        normalized_results = {self.normalize_nodeid(k): v for k, v in test_results.items()}
        failing = [t for t in fail_to_pass if normalized_results.get(self.normalize_nodeid(t)) != "passed"]
        regressions = [t for t in pass_to_pass if normalized_results.get(self.normalize_nodeid(t)) != "passed"]

        success = not failing and not regressions

        return {
            "type": "existing_tests",
            "success": success,
            "failing_tests": failing,
            "regressions": regressions,
            "output": test_out,
            "lint_status": lint_result,
        }

    def run_ruff_lint_and_fix(self, file_path: str) -> Tuple[bool, str]:
        def _run_ruff(fix: bool = False) -> Tuple[int, str]:
            args = ["ruff", "check", "--isolated", "--fix", file_path]
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

        confirm_code, confirm_out = _run_ruff(fix=False)
        if confirm_code == 0:
            self.logger.info("[Ruff] ✅ Auto-fix succeeded.")
            return True, "PASSED: AUTO-FIX - SUCCEEDED"
        else:
            return False, f"ERROR after fix: {confirm_out}"

# EOF
