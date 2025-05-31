# config_autonomous_agent
import os
from pathlib import Path
from typing import Optional

import litellm
from pydantic import Field, conint
from smolagents import LiteLLMModel, HfApiModel

from src.config.config_model import ConfigModel
from src.config.yaml_object import YamlObject

litellm.track_token_usage = True


class ConfigAgent(YamlObject):
    """
    Base configuration for each step in the workflow.

    Includes generic settings applicable across multiple phases
    and workflow steps, ensuring robust validation and behavior control.
    """

    config_model: ConfigModel = Field(
        default_factory=ConfigModel,
        description="General configuration models including LLM and system settings.",
    )
    load_cache: bool = Field(
        True, description="Load results from cache instead of recomputing."
    )
    save_cache: bool = Field(True, description="Save results to cache after computing.")
    agent_max_steps: conint(gt=0, le=10) = Field(
        30,
        description="Number of agent max retries. Must be >0.",
    )
    mock_mode: Optional[bool] = Field(
        False,
        description="If True, disables actual LLM calls and returns mocked responses (for testing).",
    )
    num_patches: conint(gt=0, le=5) = Field(
        1,
        description="Number of agent max retries. Must be >0.",
    )
    patch_prompt_path: Optional[Path] = None
    max_retries: conint(gt=0, le=10) = Field(
        7,
        description="Maximum number of retries",
    )
    max_tool_output_chars: conint(gt=0, le=10_000) = Field(
        10_000, description="Maximum tool output chars"
    )
    evaluation_detailed: bool = Field(
        True, description="Evaluation type regular or detailed."
    )
    evaluation_debug: bool = Field(False, description="Evaluation debug.")
    patch_prompt_path_first_attempt: Optional[Path] = None
    patch_prompt_path_retry: Optional[Path] = None

    def __init__(self, **data):
        super().__init__(**data)

        vendor = self.config_model.vendor_name

        if self.patch_prompt_path is None:
            prompt_paths = {
                "openai": Path("src/prompts/openai_patch_first_attempt.prompt"),
                "anthropic": Path("src/prompts/anthropic_patch_first_attempt.prompt"),
            }
            self.patch_prompt_path = prompt_paths.get(
                vendor, Path("src/prompts/openai_patch_first_attempt.prompt")
            )

        if self.patch_prompt_path_first_attempt is None:
            first_attempt_paths = {
                "openai": Path("src/prompts/openai_patch_first_attempt.prompt"),
                "anthropic": Path("src/prompts/anthropic_patch_first_attempt.prompt"),
            }
            self.patch_prompt_path_first_attempt = first_attempt_paths.get(
                vendor, Path("src/prompts/openai_patch_first_attempt.prompt")
            )

        if self.patch_prompt_path_retry is None:
            retry_paths = {
                "openai": Path("src/prompts/openai_patch_retry.prompt"),
                "anthropic": Path("src/prompts/anthropic_patch_retry.prompt"),
            }
            self.patch_prompt_path_retry = retry_paths.get(
                vendor, Path("src/prompts/openai_patch_retry.prompt")
            )

    @staticmethod
    def get_llm_wrapper(config_model):
        common_kwargs = {
            "temperature": config_model.temperature,
            "top_p": config_model.top_p,
        }
        if config_model.vendor_name.startswith("ollama"):
            return LiteLLMModel(
                model_id=f"ollama_chat/{config_model.model_name}",
                api_base="http://127.0.0.1:11434",
                api_key="YOUR_API_KEY",
                num_ctx=30_000,
                **common_kwargs,
            )
        elif config_model.vendor_name.startswith("openai"):
            return LiteLLMModel(
                model_id=config_model.model_name,
                api_base="https://api.openai.com/v1",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                **common_kwargs,
            )
        elif config_model.vendor_name.startswith("anthropic"):
            return LiteLLMModel(
                model_id=config_model.model_name,
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                custom_llm_provider="anthropic",
                **common_kwargs,
            )
        else:
            return HfApiModel(model=config_model.model_name, **common_kwargs)


# EOF
