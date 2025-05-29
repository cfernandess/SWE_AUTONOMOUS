# evaluate_patch_node_detailed.py
from langchain_core.runnables import RunnableLambda

from src.lang_graph.patch_state import PatchState
from src.models.enums import RESULT, GRAPH_STATE
from src.workflow.patch_evaluator_detailed import PatchEvaluatorDetailed


def make_evaluate_detailed_patch_node(problem, environment, config_agent):
    evaluator = PatchEvaluatorDetailed(problem, environment, config_agent)
    max_retries = config_agent.max_retries

    def evaluate_patch(state: PatchState) -> PatchState:
        attempts = state.get("evaluation_attempts", 0) + 1

        if attempts > max_retries:
            return {
                **state,
                "evaluation_result": RESULT.ERROR,
                "evaluation_err_msg": "Maximum evaluation attempts reached.",
                "evaluation_attempts": attempts,
                "graph_state": GRAPH_STATE.EVALUATE_PATCH,
            }

        try:
            result = evaluator.evaluate(patch=state["patch"])
            eval_data = result.get("evaluation", {})
            status = eval_data.get("status", "UNKNOWN")
            log_output = eval_data.get("log", "")
            report = eval_data.get("report", {})

            return {
                **state,
                "evaluation_result": (
                    RESULT.PASSED if status == "RESOLVED" else RESULT.ERROR
                ),
                "evaluation_err_msg": extract_patch_failure_summary(log_output),
                "evaluation_attempts": attempts,
                "evaluation_log": log_output,
                "evaluation_report": report,
                "graph_state": GRAPH_STATE.EVALUATE_PATCH,
            }

        except Exception as e:
            return {
                **state,
                "evaluation_result": RESULT.ERROR,
                "evaluation_err_msg": f"Evaluation crashed: {str(e)}",
                "evaluation_attempts": attempts,
                "graph_state": GRAPH_STATE.EVALUATE_PATCH,
            }

    return RunnableLambda(evaluate_patch).with_config(
        {"run_name": f"{GRAPH_STATE.EVALUATE_PATCH}_detailed"}
    )


def extract_patch_failure_summary(log: str, max_lines: int = 10) -> str:
    lines = log.strip().splitlines()
    failures = [line for line in lines if "FAILED" in line or "rejects" in line]
    summary = failures[:max_lines] if failures else lines[:max_lines]
    return "\n".join(summary) or "(No evaluation logs available.)"


# EOF
