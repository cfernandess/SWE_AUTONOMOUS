# patch_selection_agent.py
import json
from typing import List, Dict, Any

from src.agent.agent import AutonomousAgent
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem


class PatchSelectionAgent:
    def __init__(
            self,
            problem: Problem,
            environment: Environment,
            config_agent: ConfigAgent,
    ):
        self.agent = AutonomousAgent(
            problem=problem,
            environment=environment,
            config_agent=config_agent,
        )
        self.problem = problem
        self.logger = environment.logger

    def build_prompt(self, candidate_patches: List[str]) -> str:
        prompt = "You are an expert software engineer reviewing multiple proposed fixes for the following issue:\n\n"
        prompt += f"Issue:\n{self.problem.problem_statement}\n\n"
        prompt += "Here are the candidate patches:\n"
        for i, patch in enumerate(candidate_patches):
            prompt += f"\nPatch {i}:\n{patch}\n"
        prompt += """
Select the best patch based on:
- Correctness
- Minimality (make the smallest change necessary)
- Idiomatic code style

Return your answer in the following JSON format (on a single line):

{
  "selected_patch_idx": <int>,
  "reason": "<one-line explanation of why this patch is best>"
}
"""
        return prompt

    def select_best_patch(self, candidate_patches: List[str]) -> Dict[str, Any]:
        prompt = self.build_prompt(candidate_patches)
        raw_response = self.agent.run_task(prompt)
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            self.logger.error(f"[PatchSelectionAgent] Invalid JSON: {raw_response}")
            return {
                "selected_patch_idx": 0,
                "reason": "Failed to parse response. Defaulting to first patch.",
            }

# EOF
