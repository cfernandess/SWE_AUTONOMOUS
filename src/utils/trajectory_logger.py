# trajectory_logger.py
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional


class TrajectoryLogger:
    def __init__(self):
        self.steps: List[Dict[str, Any]] = []

    def log(
        self,
        step_type: str,
        content: Any,
        tool: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Log a step in the agent's trajectory.
        """
        entry = {
            "step": len(self.steps) + 1,
            "type": step_type,
            "content": content,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if tool:
            entry["tool"] = tool
        if metadata:
            entry.update(metadata)
        self.steps.append(entry)

    def to_jsonl(self) -> str:
        """
        Return the trajectory as a JSONL-formatted string.
        """
        return "\n".join(json.dumps(step) for step in self.steps)

    def save_jsonl(self, path: Path):
        """
        Save the trajectory to a .jsonl file.
        """
        path.write_text(self.to_jsonl(), encoding="utf-8")

    def get(self) -> List[Dict[str, Any]]:
        """
        Return the trajectory as a Python list.
        """
        return self.steps


# EOF
