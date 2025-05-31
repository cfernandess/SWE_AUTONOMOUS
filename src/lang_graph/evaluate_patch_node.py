# evaluate_patch_node.py
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END

from src.lang_graph.patch_state import PatchState
from src.models.enums import RESULT, GRAPH_STATE
from src.workflow.patch_evaluator import PatchEvaluator


def make_evaluate_patch_node(problem, environment, config_agent):
    evaluator = PatchEvaluator(problem, environment, config_agent)
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
            evaluation = result.get("evaluation", {})
            log_output = result.get("evaluation_log", "")
            log_summary = extract_patch_failure_summary(log_output)

            is_resolved = problem.instance_id in evaluation.get("resolved_ids", [])

            return {
                **state,
                "evaluation_result": RESULT.PASSED if is_resolved else RESULT.ERROR,
                "evaluation_err_msg": log_summary if not is_resolved else "",
                "evaluation_attempts": attempts,
                "evaluation_log": log_output,
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
        {"run_name": GRAPH_STATE.EVALUATE_PATCH}
    )


def extract_patch_failure_summary(log: str, max_lines: int = 10) -> str:
    lines = log.strip().splitlines()
    failures = [line for line in lines if "FAILED" in line or "rejects" in line]
    summary = failures[:max_lines] if failures else lines[:max_lines]
    return "\n".join(summary) or "(No evaluation logs available.)"


def route_from_evaluation(state: PatchState) -> str:
    return END


# EOF
