# problem_pipeline.py
import copy
import json
import logging
import random
from pathlib import Path
from typing import List, Dict, Tuple, Callable, Any

from rich.logging import RichHandler

from src.agent.agent import AutonomousAgent
from src.agent.patch_selection_agent import PatchSelectionAgent
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.utils.patch_evaluator import PatchEvaluator

logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)


class ProblemPipeline:
    def __init__(
            self,
            problem: Problem,
            environment: Environment,
            config_agent: ConfigAgent,
    ):
        """
        Problem Pipeline

        Args:
            problem:
            environment:
            config_agent:
        """
        self.problem = problem
        self.environment = environment
        self.config_agent = config_agent
        self.logger = self.environment.logger

        # load problem
        self.environment.load_problem(problem)
        self.config_agent = ConfigAgent()
        self.agent = AutonomousAgent(self.problem, self.environment, self.config_agent)

    def generate(self, path: Path, generator: Callable[[], Any], desc: str):
        if path.exists():
            logging.info(f"[Cache] ✅ Loaded cached {desc} from {path.name}")
            return json.loads(path.read_text())
        logging.info(f"[Cache] ❌ No cache found for {desc}, generating…")
        data = generator()
        path.write_text(json.dumps(data, indent=2))
        return data

    def summarize_eval_results(self, results: List[Dict]) -> Tuple[List[int], str]:
        passing = sorted({
            r["solution_idx"]
            for r in results
            if r["type"] == "existing_tests" and r["exit_code"] == 0
        })
        log = self.environment.logger
        if not passing:
            ran = any(r["type"] == "existing_tests" for r in results)
            if not ran:
                log.error("[Evaluator] ❌ No patches applied successfully.")
                return [], "no_valid"
            log.warning("[Evaluator] ⚠️ All patches failed the test suite.")
            return [], "no_passing"
        log.info(f"[Evaluator] ✅ {len(passing)} patch(es) passed.")
        return passing, "some_passing"

    def generate_candidates(self):
        patch_file = self.environment.root_output / f"{self.environment.instance_id}.patches.json"
        test_file = self.environment.root_output / f"{self.environment.instance_id}.tests.json"

        def gen_patch_candidates():
            return [
                self._spawn_agent_with_variation(i).generate_patch()
                for i in range(self.config_agent.num_patches)
            ]

        def gen_test_candidates():
            return [
                self._spawn_agent_with_variation(i).generate_patch_test()
                for i in range(self.config_agent.num_tests)
            ]

        solution_patches = self.generate(patch_file, gen_patch_candidates, "solution patches")
        test_patches = self.generate(test_file, gen_test_candidates, "test patches")

        return solution_patches, test_patches

    def evaluate(self, solution_patches, test_patches):
        eval_file = self.environment.root_output / f"{self.environment.instance_id}.eval.json"

        def _run():
            evaluator = PatchEvaluator(self.problem, self.environment, self.config_agent)
            return evaluator.evaluate(solution_patches, test_patches)

        return self.generate(eval_file, _run, "evaluation results")

    def select(self, solution_patches, results):
        decision_file = self.environment.root_output / f"{self.environment.instance_id}.decision.json"

        def _run():
            passing, status = self.summarize_eval_results(results)
            if passing:
                filtered = [solution_patches[i] for i in passing]
                original = passing
            else:
                filtered = solution_patches
                original = list(range(len(solution_patches)))

            selector = PatchSelectionAgent(self.problem, self.environment, self.config_agent)
            choice = selector.select_best_patch(filtered)
            choice.update({
                "original_indices": original,
                "eval_status": status
            })
            return choice

        return self.generate(decision_file, _run, "final decision")

    def run(self):
        sols, tests = self.generate_candidates()
        results = self.evaluate(sols, tests)
        decision = self.select(sols, results)
        idx = decision["selected_patch_idx"]
        orig = decision["original_indices"][idx]
        self.environment.logger.info(f"[Pipeline] ✅ Final decision: Patch {idx} (orig {orig})")

    def _spawn_agent_with_variation(self, index: int) -> AutonomousAgent:
        config_agent = copy.deepcopy(self.config_agent)
        if index == 0:
            config_agent.config_model.temperature = 0.0
            config_agent.config_model.top_p = 1.0
        else:
            # Stochastic sampling for diversity
            config_agent.config_model.temperature = random.uniform(0.8, 1.0)
            config_agent.config_model.top_p = random.uniform(0.9, 1.0)

        return AutonomousAgent(
            problem=self.problem,
            environment=self.environment,
            config_agent=config_agent,
        )
# EOF
