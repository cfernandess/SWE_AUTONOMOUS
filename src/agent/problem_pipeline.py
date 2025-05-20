import json
import logging
from pathlib import Path

from rich.logging import RichHandler

from src.agent.agent import AutonomousAgent
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


class ProblemPipeline:
    def __init__(
        self,
        problem: Problem,
        environment: Environment,
        config_agent: ConfigAgent,
    ):
        self.problem = problem
        self.environment = environment
        self.config_agent = config_agent
        self.logger = environment.logger

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

    def generate(self, path: Path, generator, desc: str):
        if path.exists():
            self.logger.info(f"[Cache] ✅ Loaded cached {desc} from {path.name}")
            return json.loads(path.read_text())

        self.logger.info(f"[Cache] ❌ No cache found for {desc}, generating...")
        data = generator()
        self.logger.info(f"[Cache] ✅ Finished generating {desc}")
        path.write_text(json.dumps(data, indent=2))
        return data

    def generate_patch(self) -> str:
        self.logger.info("[Pipeline] 🧠 Generating single patch candidate...")
        patch_file = (
            self.environment.output_path / f"{self.environment.instance_id}.patch.json"
        )

        def run_agent():
            agent = AutonomousAgent(
                problem=self.problem,
                environment=self.environment,
                config_agent=self.config_agent,
                tools=self.tools,
            )
            return agent.generate_patch()

        patch = self.generate(patch_file, run_agent, "single solution patch")
        return patch

    def run(self):
        self.logger.info("[Pipeline] 🚀 Starting simplified single-patch pipeline...")

        patch = self.generate_patch()
        self.logger.info("[Pipeline] ✅ Patch generated.")

        self.logger.info("[Pipeline] 📊 Evaluating generated patch...")
        evaluator = PatchEvaluator(
            problem=self.problem,
            environment=self.environment,
            config_agent=self.config_agent,
        )
        results = evaluator.evaluate(json.dumps({"diff": self.problem.patch}))

        eval_file = (
            self.environment.output_path / f"{self.environment.instance_id}.eval.json"
        )
        eval_file.write_text(json.dumps(results, indent=2))
        self.logger.info("[Pipeline] 🧾 Evaluation results saved.")

        return {
            "patch": patch,
            "evaluation": results,
        }
