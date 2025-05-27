# sequential_thinking_tool.py
from time import perf_counter

from smolagents.tools import Tool

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem


class SequentialThinkingTool(Tool):
    name = "sequential_thinker"
    description = "Iteratively reasons through steps before producing a final answer."

    inputs = {
        "goal": {
            "type": "string",
            "description": "Task or question to solve step by step.",
        },
        "problem_statement": {
            "type": "string",
            "description": "SWE-bench problem statement.",
        },
    }
    output_type = "string"

    def __init__(
        self,
        problem: Problem,
        environment: Environment,
        config_agent: ConfigAgent,
    ):
        super().__init__()
        self.problem = problem
        self.environment = environment
        self.logger = environment.logger
        self.traj_logger = environment.traj_logger
        self.config_agent = config_agent
        self.max_steps = self.config_agent.agent_max_steps
        self.model = self.config_agent.get_llm_wrapper(
            config_model=self.config_agent.config_model
        )

    def forward(self, goal: str, problem_statement: str) -> str:
        start = perf_counter()
        thoughts = []

        for step in range(self.max_steps):
            scratchpad = "\n".join(thoughts)
            prompt = self._build_prompt(goal, problem_statement, scratchpad)

            response = self.model(
                [
                    {
                        "role": "system",
                        "content": "You are an autonomous agent solving a software issue using structured thinking.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )

            response_text = response.content  # ✅ Extract message content
            step_text = f"Step {step + 1}: {response_text.strip()}"
            thoughts.append(step_text)

            if "FINAL ANSWER:" in response_text:  # ✅ Fixed condition
                break

        if "FINAL ANSWER:" not in thoughts[-1]:
            thoughts.append("[WARNING] Reached max_steps without FINAL ANSWER.")

        full_output = "\n".join(thoughts)

        if self.traj_logger:
            self.traj_logger.log_step(
                response="",
                thought="Begin structured chain-of-thought reasoning to reach FINAL ANSWER.",
                action=f"{self.name}: structured_thinking",
                observation=full_output,
                query=[
                    {
                        "role": "system",
                        "content": "You are an autonomous agent solving a software issue using structured thinking.",
                    },
                    {
                        "role": "user",
                        "content": f"Problem:\n{problem_statement}\nGoal:\n{goal}",
                    },
                ],
                state={
                    "repo_path": str(self.environment.repo_path),
                    "max_steps": self.max_steps,
                    "duration_seconds": perf_counter() - start,
                },
            )

        return full_output

    def _build_prompt(self, goal: str, problem_statement: str, scratchpad: str) -> str:
        return f"""
You are an autonomous agent solving a software issue using structured thinking.

Problem:
{problem_statement}

Goal:
{goal}

Scratchpad:
{scratchpad}

Think step-by-step. Output your next step of reasoning.
When you are done, write: FINAL ANSWER: <your answer>
"""


# EOF
