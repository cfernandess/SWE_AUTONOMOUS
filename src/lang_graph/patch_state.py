# patch_state.py
from typing import Literal

from typing_extensions import TypedDict


class PatchState(TypedDict, total=False):
    # Control
    graph_state: str  # Current node name (for LangGraph routing)

    # Core patch info
    patch: str  # Unified diff string

    # Simplified results
    validation_result: Literal["PASSED", "ERROR"]
    validation_err_msg: str
    evaluation_result: Literal["PASSED", "ERROR"]
    evaluation_err_msg: str

    # Tracking
    attempts: int  # Retry or generation count


# EOF
