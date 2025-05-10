# prompt_template.py

from pathlib import Path
from string import Template
from typing import List

import tiktoken

from src.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.preprocess_problem import PreprocessProblem
from src.models.prompt_arg import PromptArg


class PromptTemplate:
    def __init__(
        self,
        preprocess_problem: PreprocessProblem,
        environment: Environment,
        config_agent: ConfigAgent,
        path: Path,
        prompt_args: List[PromptArg],
    ):
        self.preprocess_problem = preprocess_problem
        self.environment = environment
        self.config_agent = config_agent
        self.prompt_args = prompt_args
        self.path = path

        try:
            self.encoding = tiktoken.encoding_for_model(
                config_agent.config_model.model_name
            )
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

        self.template = self.path.read_text()

    def generate(self) -> str:
        substitutions = {}
        for arg in self.prompt_args:
            if not isinstance(arg.data, str):
                raise TypeError(
                    f"Only supports str PromptArg.data, got {type(arg.data)} for '{arg.name}'"
                )
            substitutions[arg.name] = arg.data

        prompt = Template(self.template).substitute(substitutions)
        token_count = len(self.encoding.encode(prompt))
        print(f"[SimplePromptTemplate] Tokens used: {token_count}")
        return prompt


#  EOF
