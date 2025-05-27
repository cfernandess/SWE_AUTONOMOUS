from src.lang_graph.patch_state import PatchState


def route_from_validation(state: PatchState) -> str:
    if state.get("lint_result") in {"ERROR"}:
        return "generate_patch"
    return "evaluate_patch"
