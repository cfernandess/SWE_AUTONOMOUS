# prompt_arg.py
from typing import List, Optional, Union

from pydantic import BaseModel, Field, conint, confloat

from src.models.jasonl_object import JsonlObject


class PromptArg(BaseModel):
    """
    Represents a prompt input. Supports strings or JsonlObject values, singular or list.
    """

    name: str = Field(
        ..., description="Name of the prompt argument (e.g., 'query_code')."
    )

    data: Optional[Union[str, JsonlObject, List[str], List[JsonlObject]]] = Field(
        None, description="Single or multiple values for the prompt argument."
    )

    max_token_ratio: confloat(ge=0, le=1) = Field(
        1, description="Maximum token percentage allowed for this argument."
    )
    min_token_limit: conint(ge=0) = Field(0, description="Minimum number of tokens.")
    max_token_limit: conint(le=1_000_000) = Field(
        100, description="Maximum number of tokens."
    )

    model_config = {
        "frozen": True,
        "strict": False,  # ← allow coercion from str to Path
    }


# EOF
