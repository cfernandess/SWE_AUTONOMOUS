# jasonl_object.py
import json
from typing import Optional, List
from pydantic import BaseModel, Field


class JsonlObject(BaseModel):
    """
    Base class for objects serialized to and from JSONL format.

    Provides serialization utilities, confidence metadata, and
    preprocessing methods for LLM consumption.
    """

    reason: Optional[str] = Field(
        None, description="The text reason for selected object."
    )
    model_config = {
        "frozen": True,
        "strict": False,  # ← allow coercion from str to Path
    }

    def to_json(self, exclude_none=True, pretty=False) -> str:
        if pretty:
            return self.model_dump_json(indent=2, exclude_none=exclude_none)
        return self.model_dump_json(exclude_none=exclude_none)

    @classmethod
    def from_json(cls, json_str: str) -> "JsonlObject":
        return cls.model_validate_json(json_str)

    @classmethod
    def load_jsonl(cls, file_path: str) -> List["JsonlObject"]:
        if not file_path.endswith(".jsonl"):
            raise ValueError("File extension must be .jsonl")
        with open(file_path, "r", encoding="utf-8") as f:
            return [cls.model_validate_json(line) for line in f if line.strip()]

    @classmethod
    def write_jsonl(cls, objects: List["JsonlObject"], file_path: str) -> None:
        if not file_path.endswith(".jsonl"):
            raise ValueError("File extension must be .jsonl")
        with open(file_path, "w", encoding="utf-8") as f:
            for obj in objects:
                f.write(obj.to_json() + "\n")

    @classmethod
    def preprocess_json_llm(cls, objects: List["JsonlObject"]) -> str:
        return json.dumps(
            [json.loads(obj.to_json()) for obj in objects], separators=(",", ":")
        )

# EOF
