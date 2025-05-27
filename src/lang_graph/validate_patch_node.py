# validate_patch_node.py
from langchain_core.runnables import RunnableLambda

from src.lang_graph.patch_state import PatchState
from src.tools.patch_validator_tool import PatchValidatorTool


def make_validate_patch_node(problem, environment, config_agent, max_retries: int = 3):
    tool_runner = PatchValidatorTool(problem, environment, config_agent)

    def validate_patch(state: PatchState) -> PatchState:
        patch = state.get("patch", "")
        attempts = state.get("attempts", 0)

        if attempts >= max_retries:
            return {
                **state,
                "validation_result": "ERROR",
                "validation_err_msg": "Maximum validation attempts reached",
            }

        result = tool_runner.forward(patch)

        if result.startswith("'''\nPASSED:\n\n"):
            cleaned_patch = result.removeprefix("'''\nPASSED:\n\n").removesuffix(
                "\n'''"
            )
            return {
                **state,
                "patch": cleaned_patch,
                "validation_result": "PASSED",
                "validation_err_msg": "",
            }
        elif result.startswith("'''\nERROR:\n\n"):
            err_msg = (
                result.removeprefix("'''\nERROR:\n\n").removesuffix("\n'''").strip()
            )
            return {
                **state,
                "validation_result": "ERROR",
                "validation_err_msg": err_msg,
            }

        return {
            **state,
            "validation_result": "ERROR",
            "validation_err_msg": "Unknown format from validator tool",
        }

    return RunnableLambda(validate_patch).with_config({"run_name": "validate_patch"})


def route_from_validation(state: PatchState) -> str:
    return (
        "generate_patch"
        if state.get("validation_result") == "ERROR"
        else "evaluate_patch"
    )


# EOF
