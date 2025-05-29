# patch_state.py
import json
from typing import List
from typing import TypedDict, Optional

from src.models.enums import RESULT, GRAPH_STATE
from src.models.prompt_arg import PromptArg


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
    evaluation_log: str
    evaluation_report: dict


def patch_state_to_prompt_args(state: PatchState) -> List[PromptArg]:
    return [
        PromptArg(
            name="generation_attempts", data=str(state.get("generation_attempts", 0))
        ),
        PromptArg(
            name="generation_result", data=str(state.get("generation_result", ""))
        ),
        PromptArg(
            name="generation_err_msg", data=str(state.get("generation_err_msg", ""))
        ),
        PromptArg(
            name="validation_result", data=str(state.get("validation_result", ""))
        ),
        PromptArg(
            name="validation_err_msg", data=str(state.get("validation_err_msg", ""))
        ),
        PromptArg(
            name="evaluation_result", data=str(state.get("evaluation_result", ""))
        ),
        PromptArg(
            name="evaluation_err_msg", data=str(state.get("evaluation_err_msg", ""))
        ),
        PromptArg(
            name="evaluation_log", data=str(state.get("evaluation_log", ""))[:500]
        ),
        PromptArg(
            name="evaluation_report",
            data=json.dumps(state.get("evaluation_report", {}), indent=2),
        ),
    ]


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
