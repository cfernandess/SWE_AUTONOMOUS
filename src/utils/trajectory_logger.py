# trajectory_logger.py
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class TrajectoryLogger:
    def __init__(self):
        self.steps: List[Dict[str, Any]] = []

    def log_step(
        self,
        *,
        response: str,
        thought: str,
        action: str,
        observation: str,
        query: List[Dict[str, str]],
        state: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a single trajectory step following SWE-agent format.
        """
        step = {
            "response": response,
            "thought": thought,
            "action": action,
            "observation": observation,
            "query": query,
            "state": json.dumps(state or {}),
        }
        self.steps.append(step)

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(step, ensure_ascii=False) for step in self.steps)

    def save_jsonl(self, path: Path):
        path.write_text(self.to_jsonl(), encoding="utf-8")

    def get(self) -> List[Dict[str, Any]]:
        return self.steps


# EOF
