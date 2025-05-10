import logging
import os
from typing import Dict, Any

from smolagents import ToolCallingAgent
from smolagents.models import LiteLLMModel, HfApiModel

from src.config_agent import ConfigAgent
from src.prompt_template import PromptTemplate
from src.models.environment import Environment
from src.models.preprocess_problem import PreprocessProblem
from src.models.prompt_arg import PromptArg
from src.tools.bash_tool import BashTool
from src.tools.edit_tool import EditorTool


class AutonomousAgent:
    def __init__(
        self,
        preprocess_problem: PreprocessProblem,
        environment: Environment,
        config_agent: ConfigAgent,
    ):
        """
        Initialize the SWE agent

        Args:
            preprocess_problem:
            environment:
            config_agent:
        """
        self.preprocess_problem = preprocess_problem
        self.environment = environment
        self.config_agent = config_agent
        self.logger = logging.getLogger("rich")
        # Initialize tools
        self.tools = [BashTool(), EditorTool()]
        args = [
            PromptArg(
                name="problem_statement",
                data=preprocess_problem.problem.problem_statement,
            ),
            PromptArg(name="repo_path", data=str(environment.repo_path)),
        ]
        self.prompt_template = PromptTemplate(
            preprocess_problem=preprocess_problem,
            environment=environment,
            config_agent=config_agent,
            path=environment.root_path / config_agent.prompt_path,
            prompt_args=args,
        )

        if self.config_agent.mock_mode:
            self.agent = None
            return

        if config_agent.config_model.vendor_name.startswith("ollama"):
            self.model_wrapper = LiteLLMModel(
                model_id=config_agent.config_model.lite_llm_name,
                api_base="http://localhost:11434",
                api_key="ollama",
                num_ctx=8192,
            )
        elif config_agent.config_model.vendor_name.startswith("openai"):
            self.model_wrapper = LiteLLMModel(
                model_id=config_agent.config_model.lite_llm_name,
                api_base="https://api.openai.com/v1",
                tool_choice="auto",
                api_key=os.getenv("OPENAI_API_KEY", ""),
            )
        elif config_agent.config_model.vendor_name.startswith("anthropic"):
            self.model_wrapper = LiteLLMModel(
                model_id=config_agent.config_model.lite_llm_name,
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                custom_llm_provider="anthropic",
            )
        else:
            self.model_wrapper = HfApiModel(model="")

        self.agent = ToolCallingAgent(
            tools=self.tools,
            model=self.model_wrapper,
            max_steps=config_agent.agent_max_steps,
        )

    def run(self) -> Dict[str, Any]:
        """
        Run the SWE agent on a specific repository with a PR description

        Returns:
            The agent's response
        """
        # Format the prompt for the agent
        prompt = self.prompt_template.generate()
        # Run the agent with the formatted prompt
        response = self.agent.run(prompt)

        return response
