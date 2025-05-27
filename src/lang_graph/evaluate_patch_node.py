# evaluate_patch_node.py (LangSmith-compatible)
from langchain_core.runnables import RunnableLambda
from src.workflow.patch_evaluator import PatchEvaluator
from src.lang_graph.patch_state import PatchState


def make_evaluate_patch_node(problem, environment, config_agent):
    evaluator = PatchEvaluator(problem, environment, config_agent)

    def evaluate_patch(state: PatchState) -> PatchState:
        result = evaluator.evaluate(patch=state["lint_diff"])
        resolved = problem.instance_id in result["evaluation"].get("resolved_ids", [])
        return {
            **state,
            "status": "RESOLVED" if resolved else "UNRESOLVED",
            "resolved": resolved,
        }

    # NOTE: Expected type 'RunnableConfig | None', got 'dict[str, str]' instead
    return RunnableLambda(evaluate_patch).with_config({"run_name": "evaluate_patch"})


# EOF
