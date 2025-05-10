# config_autonomous_agent
from pathlib import Path
from typing import Optional

from pydantic import Field, conint

from src.config.config_model import ConfigModel
from src.config.yaml_object import YamlObject


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
    agent_max_steps: conint(gt=1, le=5) = Field(
        10,
        description="Number of agent max retries. Must be >0.",
    )
    mock_mode: Optional[bool] = Field(
        False,
        description="If True, disables actual LLM calls and returns mocked responses (for testing).",
    )
    prompt_path: Path = Field(
        Path("src/autonomous_agent/agent.prompt"),
        description="Relative path to the main action prompt file.",
    )


# EOF
