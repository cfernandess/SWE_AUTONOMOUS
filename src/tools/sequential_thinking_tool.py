from smolagents.tools import Tool

from src.agent.agent import AutonomousAgent
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.preprocess_problem import PreprocessProblem


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
        preprocess_problem: PreprocessProblem,
        environment: Environment,
        config_agent: ConfigAgent,
        max_steps: int = 5,
    ):
        super().__init__()
        self.problem = preprocess_problem.problem
        self.environment = environment
        self.config_agent = config_agent
        self.max_steps = max_steps
        self.model = AutonomousAgent.get_llm_wrapper(
            config_model=config_agent.config_model
        )

    def forward(self, goal: str, problem_statement: str) -> str:
        thoughts = []
        for step in range(self.max_steps):
            scratchpad = "\n".join(thoughts)
            prompt = self._build_prompt(goal, problem_statement, scratchpad)
            response = self.model(prompt)
            thoughts.append(f"Step {step+1}: {response.strip()}")
            if "FINAL ANSWER:" in response:
                break

        if "FINAL ANSWER:" not in thoughts[-1]:
            thoughts.append("[WARNING] Reached max_steps without FINAL ANSWER.")

        return "\n".join(thoughts)

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
