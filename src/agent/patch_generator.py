# patch_generator.py
import json
from pathlib import Path

from src.agent.agent import AutonomousAgent
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.tools.bash_tool import BashTool
from src.tools.edit_tool import EditorTool
from src.tools.ruff_lint_tool import RuffLintTool
from src.tools.sequential_thinking_tool import SequentialThinkingTool


class PatchGenerator:
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
        self.traj_logger = environment.traj_logger

        self.tools = [
            BashTool(problem, environment, config_agent),
            EditorTool(problem, environment, config_agent),
            RuffLintTool(problem, environment, config_agent),
            SequentialThinkingTool(problem, environment, config_agent),
        ]
        self.agent = AutonomousAgent(
            problem=problem,
            environment=environment,
            config_agent=config_agent,
            tools=self.tools,
        )

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
            patch_str = self.agent.generate_patch()
            if not patch_str.strip():
                raise ValueError("Agent returned an empty patch string.")
            return patch_str

        return self.generate(patch_file, run_agent, "single solution patch")


# EOF
