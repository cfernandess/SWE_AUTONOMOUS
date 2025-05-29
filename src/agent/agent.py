# agent.py
from time import perf_counter
from typing import List, Optional

from smolagents import ToolCallingAgent, Tool

from src.agent.prompt_template import PromptTemplate
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.models.prompt_arg import PromptArg


class LLMResponseError(Exception):
    pass


class Agent:
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
        self.tools = tools if tools else []
        args = [
            PromptArg(name="problem_statement", data=problem.problem_statement),
            PromptArg(name="repo_path", data=str(environment.repo_path)),
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

        self.model_wrapper = config_agent.get_llm_wrapper(
            config_model=config_agent.config_model
        )
        self.agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model_wrapper,
            max_steps=config_agent.agent_max_steps,
        )

    def generate_patch(self) -> str:
        prompt = self.prompt_patch_template.generate()
        query = self.prompt_patch_template.get_query(prompt)

        self.traj_logger.log_step(
            response=prompt,
            thought="Generating patch with unified diff format using LLM.",
            action="llm(prompt)",
            observation="Prompt prepared for model call.",
            state={
                "repo_path": str(self.environment.repo_path),
                "model_name": self.config_agent.config_model.model_name,
            },
            query=query,
        )

        start = perf_counter()
        patch = self.run_task(prompt)
        duration = perf_counter() - start

        self.traj_logger.log_step(
            response=patch,
            thought="LLM returned patch. Captured response from agent.",
            action="ToolCallingAgent.run()",
            observation="Patch successfully generated.",
            state={
                "duration_seconds": duration,
            },
            query=query,
        )

        trajectory_path = (
            self.environment.output_path
            / f"{self.environment.instance_id}.trajectory.jsonl"
        )
        self.traj_logger.save_jsonl(trajectory_path)
        self.logger.info(f"[Agent] 🧭 Trajectory log saved to {trajectory_path}")
        self.logger.info(f"[Agent] ✅ Patch generated in {duration:.2f} seconds")
        print(f"[Agent] ✅ Patch generated in {duration:.2f} seconds")

        return patch

    def run_task(self, task: str) -> str:
        if self.config_agent.mock_mode:
            return "[MOCK] This is a mocked response."

        if self.agent is None:
            raise LLMResponseError(
                "Agent not initialized — did you forget to disable mock_mode?"
            )

        response = self.agent.run(task=task)
        return (
            response["description"].strip()
            if isinstance(response, dict) and "description" in response
            else str(response).strip()
        )


# EOF
