# evaluate_patch_node.py (LangSmith-compatible)
from langchain_core.runnables import RunnableLambda

from src.lang_graph.patch_state import PatchState
from src.workflow.patch_evaluator import PatchEvaluator


def make_evaluate_patch_node(problem, environment, config_agent):
    evaluator = PatchEvaluator(problem, environment, config_agent)

    def evaluate_patch(state: PatchState) -> PatchState:
        try:
            result = evaluator.evaluate(patch=state["patch"])
            resolved = problem.instance_id in result["evaluation"].get(
                "resolved_ids", []
            )
            return {
                **state,
                "evaluation_result": "PASSED" if resolved else "ERROR",
                "evaluation_err_msg": (
                    "" if resolved else "Patch did not resolve the issue"
                ),
            }
        except Exception as e:
            return {
                **state,
                "evaluation_result": "ERROR",
                "evaluation_err_msg": f"Evaluation failed: {str(e)}",
            }

    return RunnableLambda(evaluate_patch).with_config({"run_name": "evaluate_patch"})


# EOF
