# patch_state.py
from typing import TypedDict, Optional

from src.models.enums import RESULT, GRAPH_STATE


class PatchState(TypedDict, total=False):
    """State container for patch lifecycle in LangGraph pipeline (generate → validate → evaluate)."""

    graph_state: GRAPH_STATE
    patch: str
    gold_patch: str

    generation_result: RESULT
    generation_err_msg: Optional[str]
    generation_attempts: int

    validation_result: RESULT
    validation_err_msg: Optional[str]
    validation_attempts: int

    evaluation_result: RESULT
    evaluation_err_msg: Optional[str]
    evaluation_attempts: int


def make_initial_patch_state() -> PatchState:
    return {
        "graph_state": GRAPH_STATE.START,
        "generation_result": RESULT.INIT,
        "validation_result": RESULT.INIT,
        "evaluation_result": RESULT.INIT,
        "generation_attempts": 0,
        "validation_attempts": 0,
        "evaluation_attempts": 0,
    }


# EOF
