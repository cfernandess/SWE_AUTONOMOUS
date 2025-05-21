# agent.py
from datetime import datetime, UTC
from time import perf_counter
from typing import List, Optional

from smolagents import ToolCallingAgent, Tool

from src.agent.prompt_template import PromptTemplate
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.models.prompt_arg import PromptArg
from src.utils.repo_structure import RepoStructure
from src.utils.trajectory_logger import TrajectoryLogger


class LLMResponseError(Exception):
    """Custom exception for LLM response errors."""

    pass


class AutonomousAgent:
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
        self.tools = tools if tools else []
        self.repo_structure, _ = RepoStructure(
            repo_path=self.environment.repo_path, file_ext=[".py"]
        ).generate_structure()
        self.trajectory_logger = TrajectoryLogger()

        args = [
            PromptArg(name="problem_statement", data=problem.problem_statement),
            PromptArg(name="repo_path", data=str(environment.repo_path)),
            PromptArg(name="repo_structure", data=self.repo_structure),
        ]

        self.prompt_patch_template = PromptTemplate(
            problem=problem,
            environment=environment,
            config_agent=config_agent,
            path=environment.root_path / config_agent.patch_prompt_path,
            prompt_args=args,
        )

        if config_agent.mock_mode:
            self.agent = None
            return

        self.model_wrapper = config_agent.get_llm_wrapper(config_agent.config_model)
        self.agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model_wrapper,
            max_steps=config_agent.agent_max_steps,
        )

    def generate_patch(self) -> str:
        """
        Generates a patch for the current problem.
        Always logs trajectory and saves it to a `.trajectory.jsonl` file.
        """
        prompt = self.prompt_patch_template.generate()

        self.trajectory_logger.log(
            step_type="llm_prompt",
            content=prompt,
            metadata={
                "model_name": self.config_agent.config_model.model_name,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

        start = perf_counter()
        patch = self.run_task(prompt)
        duration = perf_counter() - start

        # Safe access with fallback defaults
        input_tokens = getattr(self.model_wrapper, "num_input_tokens", 0)
        output_tokens = getattr(self.model_wrapper, "num_output_tokens", 0)
        input_cost = getattr(self.model_wrapper, "input_cost", 0.0)
        output_cost = getattr(self.model_wrapper, "output_cost", 0.0)

        self.trajectory_logger.log(
            step_type="llm_response",
            content=patch,
            metadata={
                "model_name": self.config_agent.config_model.model_name,
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_seconds": duration,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "total_cost": input_cost + output_cost,
            },
        )

        trajectory_path = (
            self.environment.output_path
            / f"{self.environment.instance_id}.trajectory.jsonl"
        )
        self.trajectory_logger.save_jsonl(trajectory_path)
        self.logger.info(f"[Agent] 🧭 Trajectory log saved to {trajectory_path}")
        self.logger.info(
            f"[Agent] 💰 Cost summary — "
            f"input_tokens: {input_tokens:,}, "
            f"output_tokens: {output_tokens:,}, "
            f"total_cost: ${input_cost + output_cost:.6f}"
        )
        print(
            f"[Agent] 💰 Cost summary — "
            f"input_tokens: {input_tokens:,}, "
            f"output_tokens: {output_tokens:,}, "
            f"total_cost: ${input_cost + output_cost:.6f}"
        )

        return patch

    def run_task(self, task: str) -> str:
        if self.config_agent.mock_mode:
            return "[MOCK] This is a mocked response."

        if self.agent is None:
            raise LLMResponseError(
                "Agent not initialized — did you forget to disable mock_mode?"
            )

        response = self.agent.run(task=task)

        if not response:
            return ""

        if isinstance(response, dict) and "description" in response:
            return response["description"].strip()

        return str(response).strip()


# EOF
