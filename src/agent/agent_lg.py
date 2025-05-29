# agent_lg.py

from time import perf_counter
from typing import List, Optional

from smolagents import ToolCallingAgent, Tool

from src.agent.prompt_template import PromptTemplate
from src.config.config_agent import ConfigAgent
from src.lang_graph.patch_state import PatchState
from src.models.environment import Environment
from src.models.problem import Problem
from src.models.prompt_arg import PromptArg


class AgentLG:
    def __init__(
        self,
        problem: Problem,
        environment: Environment,
        config_agent: ConfigAgent,
        tools: Optional[List[Tool]] = None,
    ):
        self.problem = problem
        self.environment = environment
        self.config_agent = config_agent
        self.logger = environment.logger
        self.traj_logger = environment.traj_logger
        self.tools = tools or []

        if config_agent.mock_mode:
            self.agent = None
            return

        self.model_wrapper = config_agent.get_llm_wrapper(config_agent.config_model)
        self.agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model_wrapper,
            max_steps=config_agent.agent_max_steps,
        )

    def generate_patch(self, state: PatchState) -> str:
        args = [
            PromptArg(name="problem_statement", data=self.problem.problem_statement),
            PromptArg(name="repo_path", data=str(self.environment.repo_path)),
            PromptArg(
                name="generation_err_msg", data=str(state.get("generation_err_msg", ""))
            ),
            PromptArg(
                name="validation_err_msg", data=str(state.get("validation_err_msg", ""))
            ),
            PromptArg(
                name="evaluation_err_msg", data=str(state.get("evaluation_err_msg", ""))
            ),
            PromptArg(name="attempt", data=str(state.get("generation_attempts", 0))),
        ]

        template = PromptTemplate(
            problem=self.problem,
            environment=self.environment,
            config_agent=self.config_agent,
            path=self.environment.root_path / self.config_agent.patch_prompt_path,
            prompt_args=args,
        )

        prompt = template.generate()
        query = template.get_query(prompt)

        self.traj_logger.log_step(
            response=prompt,
            thought="Generating retry-aware patch with LLM using PatchState.",
            action="llm(prompt)",
            observation="Prompt prepared with contextual error messages and attempt count.",
            state=dict(state),
            query=query,
        )

        start = perf_counter()
        patch = self._run_task(prompt)
        duration = perf_counter() - start

        self.traj_logger.log_step(
            response=patch,
            thought="Patch generated from retry-aware LLM agent.",
            action="ToolCallingAgent.run()",
            observation="Patch returned successfully.",
            state={"duration_seconds": duration},
            query=query,
        )

        trajectory_path = (
            self.environment.output_path
            / f"{self.environment.instance_id}_attempt_{state.get('generation_attempts', 0)}.trajectory.jsonl"
        )
        self.traj_logger.save_jsonl(trajectory_path)
        self.logger.info(f"[LGAgent] 🧭 Trajectory saved to {trajectory_path}")
        return patch

    def _run_task(self, prompt: str) -> str:
        if self.config_agent.mock_mode:
            return "[MOCK] This is a mocked response."

        if not self.agent:
            raise RuntimeError("Agent not initialized (mock_mode may be True).")

        response = self.agent.run(task=prompt)
        return (
            response["description"].strip()
            if isinstance(response, dict) and "description" in response
            else str(response).strip()
        )


# EOF
