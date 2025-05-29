# validate_patch_node.py
import json

from langchain_core.runnables import RunnableLambda
from langgraph.graph import END

from src.lang_graph.patch_state import PatchState
from src.models.enums import RESULT, GRAPH_STATE
from src.tools.patch_validator_tool import PatchValidatorTool


def make_validate_patch_node(problem, environment, config_agent):
    tool_runner = PatchValidatorTool(problem, environment, config_agent)
    max_retries = config_agent.max_retries

    def validate_patch(state: PatchState) -> PatchState:
        patch = state.get("patch", "")
        attempts = state.get("validation_attempts", 0) + 1

        if attempts > max_retries:
            return {
                **state,
                "validation_result": RESULT.ERROR,
                "validation_err_msg": "Maximum validation attempts reached.",
                "validation_attempts": attempts,
                "graph_state": GRAPH_STATE.VALIDATE_PATCH,
            }

        try:
            result = json.loads(tool_runner.forward(patch))
        except json.JSONDecodeError as e:
            return {
                **state,
                "validation_result": RESULT.ERROR,
                "validation_err_msg": f"Validator returned invalid JSON: {e}",
                "validation_attempts": attempts,
                "graph_state": GRAPH_STATE.VALIDATE_PATCH,
            }

        if result.get("status") == "PASSED":
            cleaned_patch = result.get("cleaned_patch", patch)
            return {
                **state,
                "patch": cleaned_patch,
                "validation_result": RESULT.PASSED,
                "validation_err_msg": "",
                "validation_attempts": attempts,
                "graph_state": GRAPH_STATE.VALIDATE_PATCH,
            }

        if result.get("status") == "ERROR":
            return {
                **state,
                "validation_result": RESULT.ERROR,
                "validation_err_msg": result.get("error_message", "Unknown error"),
                "validation_attempts": attempts,
                "graph_state": GRAPH_STATE.VALIDATE_PATCH,
            }

        # Unexpected output
        return {
            **state,
            "validation_result": RESULT.ERROR,
            "validation_err_msg": f"Unexpected validator result: {result}",
            "validation_attempts": attempts,
            "graph_state": GRAPH_STATE.VALIDATE_PATCH,
        }

    return RunnableLambda(validate_patch).with_config(
        {"run_name": GRAPH_STATE.VALIDATE_PATCH}
    )


def route_from_validation(state: PatchState) -> str:
    if state.get("validation_result") == RESULT.ERROR:
        return (
            GRAPH_STATE.GENERATE_PATCH
            if state.get("validation_attempts", 0) < 3
            else END
        )
    return GRAPH_STATE.EVALUATE_PATCH


# EOF
