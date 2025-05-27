from typing import Literal
from typing_extensions import TypedDict


class PatchState(TypedDict, total=False):
    # Control
    graph_state: str  # Current node name (for LangGraph routing)

    # Core patch info
    patch: str  # Unified diff string

    # Lint validation result
    lint_result: Literal["PASSED", "PASSED: AUTO-FIX - SUCCEEDED", "ERROR"]
    lint_diff: str  # Optional corrected diff (only if auto-fixed)

    # Evaluation result
    status: Literal["RESOLVED", "UNRESOLVED", "UNKNOWN"]
    resolved: bool  # True if patch resolved the issue

    # Tracking
    attempts: int  # Retry or generation count

    target_path: str
