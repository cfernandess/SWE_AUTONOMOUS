# patch_evaluator.py
from enum import Enum
from typing import List, Dict

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.utils.docker_utils import apply_patch, setup_repo, run_command


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
        self.base_commit = self.problem.problem.base_commit
        self.test_framework = TestFramework(self.problem.test_framework)

    def run_tests(self, test_cmd: str) -> (str, int):
        if not test_cmd:
            return "[SKIPPED] No test command specified", -1
        return run_command(test_cmd, cwd=self.repo_path)

    def evaluate(
            self,
            solution_patches: List[str],
            test_patches: List[str],
    ) -> List[Dict]:
        results = []
        test_cmd = self.get_test_command(self.test_framework)

        for i, solution_patch in enumerate(solution_patches):
            setup_repo(self.repo_path, self.base_commit)
            patch_out, patch_code = apply_patch(solution_patch, self.repo_path)

            if patch_code != 0:
                results.append({
                    "solution_idx": i,
                    "test_idx": None,
                    "type": "apply_patch_failed",
                    "output": patch_out,
                })
                continue

            # Run the existing test suite
            test_out, test_code = self.run_tests(test_cmd)
            results.append({
                "solution_idx": i,
                "test_idx": None,
                "type": "existing_tests",
                "exit_code": test_code,
                "output": test_out,
            })

            for j, test_patch in enumerate(test_patches):
                setup_repo(self.repo_path, self.base_commit)

                _, code1 = apply_patch(solution_patch, self.repo_path)
                if code1 != 0:
                    results.append({
                        "solution_idx": i,
                        "test_idx": j,
                        "type": "apply_solution_failed",
                    })
                    continue

                _, code2 = apply_patch(test_patch, self.repo_path)
                if code2 != 0:
                    results.append({
                        "solution_idx": i,
                        "test_idx": j,
                        "type": "apply_test_failed",
                    })
                    continue

                test_out, test_code = self.run_tests(test_cmd)
                results.append({
                    "solution_idx": i,
                    "test_idx": j,
                    "type": "test_patch_eval",
                    "exit_code": test_code,
                    "output": test_out,
                })

        return results

    @staticmethod
    def get_test_command(framework: TestFramework) -> str:
        if framework == TestFramework.PYTEST:
            return "pytest -q"
        elif framework == TestFramework.UNITTEST:
            return "python -m unittest discover"
        elif framework == TestFramework.TOX:
            return "tox -e test"
        elif framework == TestFramework.NO_TESTS:
            return ""
        raise ValueError(f"Unsupported test framework: {framework}")

# EOF
