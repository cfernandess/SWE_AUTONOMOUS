# agent.py
from smolagents import ToolCallingAgent
from src.agent.prompt_template import PromptTemplate
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.models.prompt_arg import PromptArg
from src.tools.bash_tool import BashTool
from src.tools.edit_tool import EditorTool
from src.tools.sequential_thinking_tool import SequentialThinkingTool


class LLMResponseError(Exception):
    """Custom exception for LLM response errors."""

    pass


class AutonomousAgent:
    def __init__(
            self,
            problem: Problem,
            environment: Environment,
            config_agent: ConfigAgent,
    ):
        """
        Initialize the SWE agent

        Args:
            problem:
            environment:
            config_agent:
        """
        self.problem = problem
        self.environment = environment
        self.config_agent = config_agent
        self.logger = environment.logger
        # Initialize tools
        self.tools = [
            BashTool(),
            EditorTool(),
            SequentialThinkingTool(
                problem=problem,
                environment=environment,
                config_agent=config_agent,
            ),
        ]
        args = [
            PromptArg(
                name="problem_statement",
                data=problem.problem_statement,
            ),
            PromptArg(name="repo_path", data=str(environment.repo_path)),
        ]
        self.prompt_patch_template = PromptTemplate(
            problem=problem,
            environment=environment,
            config_agent=config_agent,
            path=environment.root_path / config_agent.patch_prompt_path,
            prompt_args=args,
        )
        self.prompt_test_patch_template = PromptTemplate(
            problem=problem,
            environment=environment,
            config_agent=config_agent,
            path=environment.root_path / config_agent.test_patch_prompt_path,
            prompt_args=args,
        )

        if self.config_agent.mock_mode:
            self.agent = None
            return

        self.model_wrapper = self.config_agent.get_llm_wrapper(config_agent.config_model)

        self.agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model_wrapper,
            max_steps=config_agent.agent_max_steps,
        )

    def generate_patch(self) -> str:
        """
        Generates a patch for the current problem.
        Can be called multiple times to sample variations.
        """
        prompt = self.prompt_patch_template
        return self.run_task(prompt.generate())

    def generate_patch_test(self) -> str:
        """
        Generates a patch test that ideally reproduces the failure.
        Can be reused to validate one or more patches.
        """
        prompt = self.prompt_test_patch_template
        return self.run_task(prompt.generate())

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

#  EOF
