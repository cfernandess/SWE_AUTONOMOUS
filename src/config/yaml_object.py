# yaml_object.py

from pathlib import Path

import yaml
from pydantic import BaseModel


class YamlObject(BaseModel):
    """
    Base class that supports YAML serialization and deserialization.
    Includes cache-related options.
    """

    def to_yaml_file(self, file_path: str | Path) -> None:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                self.model_dump(mode="json"),
                f,
                default_flow_style=False,
                sort_keys=False,
            )

    @classmethod
    def from_yaml_file(cls, file_path: str | Path) -> "YamlObject":
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


    # EOF
