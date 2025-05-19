# config_model.py
from functools import cached_property
from typing import Literal, Optional, List

import litellm
from pydantic import Field, conint, confloat

from src.config.yaml_object import YamlObject


class ConfigModel(YamlObject):
    """
    Configuration for Large Language Model (LLM) generation.

    Includes models and vendor details, generation parameters, and
    dynamically retrieves models metadata (e.g., max input tokens) via LiteLLM.
    """

    model_name: str = Field(
        "gpt-4o", description="Name of the LLM model (e.g., gpt-4o)."
    )
    vendor_name: Literal["openai", "anthropic", "cohere"] = Field(
        "openai", description="Vendor of the LLM model."
    )
    generation_tokens: conint(gt=0, le=10_000) = Field(
        5_000, description="Maximum tokens to generate (must be > 0)."
    )
    temperature: confloat(ge=0, le=2) = Field(
        0.0, description="Temperature setting for LLM sampling (0 ≤ temperature ≤ 2)."
    )
    top_p: confloat(ge=0, le=1) = Field(
        1.0, description="Top-p (nucleus) sampling cutoff (0 ≤ top_p ≤ 1)."
    )
    stop: Optional[List[str]] = Field(
        default=None,
        description="Optional list of stop sequences to truncate LLM output.",
    )
    seed: Optional[int] = Field(
        default=None,
        description="Optional seed for reproducible sampling (if supported).",
    )

    @property
    def lite_llm_name(self) -> str:
        return self.model_name

    @cached_property
    def model_info(self) -> dict:
        try:
            return litellm.get_model_info(
                model=self.model_name, custom_llm_provider=self.vendor_name
            )
        except Exception:
            return {}

    @property
    def max_tokens(self) -> int:
        """
        Maximum input context tokens from models metadata (LiteLLM).
        """
        return self.model_info.get("max_tokens", 10_000)


# EOF
