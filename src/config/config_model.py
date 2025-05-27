# config_model.py
from typing import Literal, Optional, List

from pydantic import Field, conint, confloat

from src.config.yaml_object import YamlObject


class ConfigModel(YamlObject):
    """
    Configuration for Large Language Model (LLM) generation.

    Includes models and vendor details, generation parameters, and
    dynamically retrieves models metadata (e.g., max input tokens) via LiteLLM.
    """

    model_name: str = Field(
        "claude-3-opus-20240229", description="Name of the LLM model (e.g., gpt-4o)."
    )
    vendor_name: Literal["openai", "anthropic", "cohere"] = Field(
        "anthropic", description="Vendor of the LLM model."
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


# EOF
