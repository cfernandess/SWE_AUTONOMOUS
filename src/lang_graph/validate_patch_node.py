# validate_patch_node.py (LangSmith-compatible)
import re

from langchain_core.runnables import RunnableLambda

from src.lang_graph.patch_state import PatchState
from src.tools.ruff_lint_tool import RuffLintTool


def make_validate_patch_node(problem, environment, config_agent, max_retries: int = 3):
    tool_runner = RuffLintTool(problem, environment, config_agent)

    def validate_patch(state: PatchState) -> PatchState:
        patch = state.get("patch", "")
        attempts = state.get("attempts", 0)

        if attempts >= max_retries:
            return {**state, "lint_result": "SKIPPED", "lint_diff": patch}

        def _extract_chunks(patch: str):
            parts = re.split(r"^diff --git a/(.+?) b/\1\n", patch, flags=re.MULTILINE)
            return [
                {
                    "path": parts[i],
                    "diff": f"diff --git a/{parts[i]} b/{parts[i]}\n{parts[i+1]}",
                }
                for i in range(1, len(parts), 2)
            ]

        def _has_valid_hunk(diff: str):
            return re.search(r"^@@ -\d+,\d+ \+\d+,\d+ @@", diff, re.MULTILINE)

        try:
            chunks = _extract_chunks(patch)
        except Exception:
            return {**state, "lint_result": "ERROR", "lint_diff": ""}

        for chunk in chunks:
            if not _has_valid_hunk(chunk["diff"]):
                return {**state, "lint_result": "ERROR", "lint_diff": ""}
            result = tool_runner.forward([chunk])
            if result.startswith("ERROR"):
                return {**state, "lint_result": "ERROR", "lint_diff": ""}

        return {**state, "lint_result": "PASSED", "lint_diff": patch}

    return RunnableLambda(validate_patch).with_config({"run_name": "validate_patch"})


def route_from_validation(state: PatchState) -> str:
    if state.get("lint_result") in {"ERROR"}:
        return "generate_patch"
    return "evaluate_patch"


# EOF
