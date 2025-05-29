# patch_generator_lg.py
from src.agent.agent_lg import AgentLG
from src.config.config_agent import ConfigAgent
from src.lang_graph.patch_state import PatchState
from src.models.environment import Environment
from src.models.problem import Problem
from src.tools.bash_tool import BashTool
from src.tools.edit_tool import EditorTool
from src.tools.patch_validator_tool import PatchValidatorTool
from src.tools.sequential_thinking_tool import SequentialThinkingTool


class PatchGeneratorLG:
    def __init__(
        self, problem: Problem, environment: Environment, config_agent: ConfigAgent
    ):
        self.problem = problem
        self.environment = environment
        self.config_agent = config_agent
        self.logger = environment.logger

        self.tools = [
            BashTool(problem, environment, config_agent),
            EditorTool(problem, environment, config_agent),
            PatchValidatorTool(problem, environment, config_agent),
            SequentialThinkingTool(problem, environment, config_agent),
        ]

        self.agent = AgentLG(
            problem=problem,
            environment=environment,
            config_agent=config_agent,
            tools=self.tools,
        )

    def generate_patch(self, state: PatchState) -> str:
        attempt = state.get("generation_attempts", 0)
        err_msg = state.get("generation_err_msg") or ""
        prev_val_err = state.get("validation_err_msg") or ""
        prev_eval_err = state.get("evaluation_err_msg") or ""

        patch_path = (
            self.environment.output_path / f"{self.environment.instance_id}.patch"
        )

        if patch_path.exists() and self.config_agent.load_cache:
            self.logger.info(f"[Cache] ✅ Loaded cached patch from {patch_path.name}")
            return patch_path.read_text()

        if attempt > 0:
            self.logger.info(f"[Retry] 🧠 Attempt {attempt + 1} to generate patch.")
            self.logger.info(f"[Retry] ⚠️ Previous generation error: {err_msg}")
            self.logger.info(f"[Retry] ⚠️ Previous validation error: {prev_val_err}")
            self.logger.info(f"[Retry] ⚠️ Previous evaluation error: {prev_eval_err}")

        patch_str = self.agent.generate_patch(state)
        if not patch_str.strip():
            raise ValueError("Agent returned an empty patch string.")

        self.environment.traj_logger.log_step(
            response=patch_str,
            thought=f"Patch generated in retry attempt {attempt + 1}.",
            action="agent.generate_patch()",
            observation="Retry patch candidate successfully produced.",
            query=[
                f"generation_err: {err_msg}",
                f"validation_err: {prev_val_err}",
                f"evaluation_err: {prev_eval_err}",
            ],
            state=state,
        )

        patch_path.write_text(patch_str)
        self.logger.info(f"[Cache] ✅ Saved patch to {patch_path.name}")
        return patch_str


# EOF
