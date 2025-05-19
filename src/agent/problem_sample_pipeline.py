# problem_sample_pipeline.py
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
from src.tools.bash_tool import BashTool
from src.tools.edit_tool import EditorTool
from src.tools.ruff_lint_tool import RuffLintTool
from src.tools.sequential_thinking_tool import SequentialThinkingTool
from src.utils.patch_evaluator import PatchEvaluator

logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)


class ProblemSamplePipeline:
    def __init__(
        self,
        problem: Problem,
        environment: Environment,
        config_agent: ConfigAgent,
    ):
        self.problem = problem
        self.environment = environment
        self.config_agent = config_agent
        self.logger = self.environment.logger
        self.config_agent = ConfigAgent()

        self.tools = [
            BashTool(),
            EditorTool(),
            RuffLintTool(environment=environment, config_agent=config_agent),
            SequentialThinkingTool(
                problem=problem,
                environment=environment,
                config_agent=config_agent,
            ),
        ]

    def generate(self, path: Path, generator: Callable[[], Any], desc: str):
        if path.exists():
            self.logger.info(f"[Cache] ✅ Loaded cached {desc} from {path.name}")
            return json.loads(path.read_text())
        self.logger.info(f"[Cache] ❌ No cache found for {desc}, generating...")
        try:
            data = generator()
            self.logger.info(f"[Cache] ✅ Finished generating {desc}")
            path.write_text(json.dumps(data, indent=2))
            return data
        except Exception as e:
            self.logger.error(f"[Cache] ❌ Failed generating {desc}: {e}")
            raise

    def summarize_eval_results(self, results: List[Dict]) -> Tuple[List[int], str]:
        passing = sorted(
            {
                r["solution_idx"]
                for r in results
                if r["type"] == "existing_tests" and r["exit_code"] == 0
            }
        )
        if not passing:
            ran = any(r["type"] == "existing_tests" for r in results)
            if not ran:
                self.logger.error("[Evaluator] ❌ No patches applied successfully.")
                return [], "no_valid"
            self.logger.warning("[Evaluator] ⚠️ All patches failed the test suite.")
            return [], "no_passing"

        self.logger.info(f"[Evaluator] ✅ {len(passing)} patch(es) passed the test suite.")
        return passing, "some_passing"

    def generate_candidates(self):
        self.logger.info("[Pipeline] 📦 Generating patch and test candidates...")
        patch_file = self.environment.output_path / f"{self.environment.instance_id}.patches.json"
        test_file = self.environment.output_path / f"{self.environment.instance_id}.tests.json"

        def gen_patch_candidates():
            self.logger.info(f"[Generator] 🔁 Generating {self.config_agent.num_patches} solution patches...")
            return [
                self._spawn_agent_with_variation(i).generate_patch()
                for i in range(self.config_agent.num_patches)
            ]

        def gen_test_candidates():
            self.logger.info(f"[Generator] 🔁 Generating {self.config_agent.num_tests} test patches...")
            return [
                self._spawn_agent_with_variation(i).generate_patch_test()
                for i in range(self.config_agent.num_tests)
            ]

        solution_patches = self.generate(patch_file, gen_patch_candidates, "solution patches")
        test_patches = self.generate(test_file, gen_test_candidates, "test patches")

        self.logger.info(f"[Pipeline] ✅ Generated {len(solution_patches)} solution and {len(test_patches)} test patches.")
        return solution_patches, test_patches

    def evaluate(self, solution_patches, test_patches):
        self.logger.info("[Pipeline] 🧪 Running evaluation on generated patches...")
        eval_file = self.environment.output_path / f"{self.environment.instance_id}.eval.json"

        def _run():
            evaluator = PatchEvaluator(self.problem, self.environment, self.config_agent)
            return evaluator.evaluate(solution_patches, test_patches)

        results = self.generate(eval_file, _run, "evaluation results")
        self.logger.info(f"[Pipeline] 🧾 Evaluation produced {len(results)} result entries.")
        return results

    def select(self, solution_patches, results):
        self.logger.info("[Pipeline] 🤖 Selecting best patch based on evaluation results...")
        decision_file = self.environment.output_path / f"{self.environment.instance_id}.decision.json"

        def _run():
            passing, status = self.summarize_eval_results(results)
            if passing:
                filtered = [solution_patches[i] for i in passing]
                original = passing
                self.logger.info(f"[Selection] 🟢 {len(passing)} candidate(s) passed. Selecting among them.")
            else:
                filtered = solution_patches
                original = list(range(len(solution_patches)))
                self.logger.info(f"[Selection] 🟡 No passing patches. Falling back to all {len(filtered)} candidates.")

            selector = PatchSelectionAgent(self.problem, self.environment, self.config_agent)
            choice = selector.select_best_patch(filtered)
            choice.update({"original_indices": original, "eval_status": status})
            self.logger.info(f"[Selection] ✅ Selected patch index {choice['selected_patch_idx']} (original {original[choice['selected_patch_idx']]})")
            return choice

        return self.generate(decision_file, _run, "final decision")

    def run(self):
        self.logger.info("[Pipeline] 🚀 Starting problem-solving pipeline...")
        patches, tests = self.generate_candidates()
        results = self.evaluate(patches, tests)
        decision = self.select(patches, results)

        idx = decision["selected_patch_idx"]
        orig = decision["original_indices"][idx]
        self.logger.info(f"[Pipeline] 🏁 Final decision: Patch {idx} (original index {orig}) selected.")
        self.logger.info("[Pipeline] ✅ Pipeline complete.")

    def _spawn_agent_with_variation(self, index: int) -> AutonomousAgent:
        config_agent = copy.deepcopy(self.config_agent)
        if index == 0:
            config_agent.config_model.temperature = 0.0
            config_agent.config_model.top_p = 1.0
        else:
            config_agent.config_model.temperature = random.uniform(0.8, 1.0)
            config_agent.config_model.top_p = random.uniform(0.9, 1.0)

        self.logger.debug(
            f"[AgentSpawn] 🔁 Instantiating agent {index} with temp={config_agent.config_model.temperature:.2f}, "
            f"top_p={config_agent.config_model.top_p:.2f}"
        )

        return AutonomousAgent(
            problem=self.problem,
            environment=self.environment,
            config_agent=config_agent,
            tools=self.tools,
        )


# EOF
