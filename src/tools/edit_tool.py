# edit_tool.py
import os
from pathlib import Path
from time import perf_counter

from smolagents.tools import Tool

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem


def resolve_path(repo_path: Path, input_path: str) -> Path:
    path = Path(input_path)
    return (repo_path / path).resolve() if not path.is_absolute() else path


class EditorTool(Tool):
    name = "str_replace_editor"
    description = """Custom editing tool for viewing, creating, editing files.\n
* `view` shows file content with line numbers or directory listing (2 levels deep).\n
* `create` creates a new file.\n
* `str_replace` replaces a unique text block.\n
* `insert` inserts text after a line number.\n
* `undo_edit` is not implemented.\n
"""
    inputs = {
        "command": {
            "type": "string",
            "enum": ["view", "create", "str_replace", "insert", "undo_edit"],
            "description": "Command to run",
        },
        "path": {
            "type": "string",
            "description": "Absolute or relative path to file or directory",
        },
        "file_text": {
            "type": "string",
            "description": "File contents for create command",
            "nullable": True,
        },
        "old_str": {
            "type": "string",
            "description": "String to replace in `str_replace`",
            "nullable": True,
        },
        "new_str": {
            "type": "string",
            "description": "Replacement string or inserted text",
            "nullable": True,
        },
        "insert_line": {
            "type": "integer",
            "description": "Line number to insert text after",
            "nullable": True,
        },
        "view_range": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Optional view line range [start, end]",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(
        self,
        problem: Problem,
        environment: Environment,
        config_agent: ConfigAgent,
    ):
        super().__init__()
        self.problem = problem
        self.environment = environment
        self.logger = environment.logger
        self.traj_logger = environment.traj_logger
        self.config_agent = config_agent

    def forward(
        self,
        command: str,
        path: str,
        file_text: str = "",
        old_str: str = "",
        new_str: str = "",
        insert_line: int = 0,
        view_range: list[int] = None,
    ) -> str:
        start = perf_counter()
        resolved_path = None

        try:
            resolved_path = resolve_path(self.environment.repo_path, path)

            if not str(resolved_path).startswith(str(self.environment.repo_path)):
                return (
                    f"Error: Access outside repository is not allowed: {resolved_path}"
                )

            if command == "view":
                if resolved_path.is_dir():
                    files = []
                    for root, _, filenames in os.walk(resolved_path, topdown=True):
                        level = root.replace(str(resolved_path), "").count(os.sep)
                        if level <= 2:
                            indent = " " * 4 * level
                            files.append(f"{indent}{os.path.basename(root)}/")
                            subindent = " " * 4 * (level + 1)
                            for f in filenames:
                                if not f.startswith("."):
                                    files.append(f"{subindent}{f}")
                    result = "\n".join(files)
                elif resolved_path.is_file():
                    with resolved_path.open("r") as f:
                        full_content = f.readlines()

                    if view_range:
                        start_line = max(0, view_range[0] - 1)
                        end_line = (
                            view_range[1] if view_range[1] != -1 else len(full_content)
                        )
                        content = full_content[start_line:end_line]
                        line_offset = start_line
                    else:
                        content = full_content
                        line_offset = 0
                        start_line = 0
                        end_line = len(content)

                    header = f"[Showing lines {start_line + 1} to {end_line} of {len(full_content)}]\n"
                    result = header + "".join(
                        [
                            f"{i + 1 + line_offset:4d} {line}"
                            for i, line in enumerate(content)
                        ]
                    )
                else:
                    result = f"Error: {resolved_path} is not a file or directory."

            elif command == "create":
                if resolved_path.exists():
                    result = f"Error: {resolved_path} already exists."
                else:
                    os.makedirs(resolved_path.parent, exist_ok=True)
                    with resolved_path.open("w") as f:
                        f.write(file_text)
                    result = f"File created: {resolved_path}"

            elif command == "str_replace":
                if not resolved_path.is_file():
                    result = f"Error: File does not exist: {resolved_path}"
                else:
                    with resolved_path.open("r") as f:
                        content = f.read()
                    occurrences = content.count(old_str)
                    if occurrences == 0:
                        result = f"Error: old_str not found in {resolved_path}"
                    elif occurrences > 1:
                        result = f"Error: old_str appears {occurrences} times, must be unique"
                    else:
                        with resolved_path.open("w") as f:
                            f.write(content.replace(old_str, new_str))
                        result = f"Successfully replaced content in {resolved_path}"

            elif command == "insert":
                if not resolved_path.is_file():
                    result = f"Error: File does not exist: {resolved_path}"
                else:
                    try:
                        insert_line = int(insert_line)
                    except ValueError:
                        result = "Error: insert_line must be an integer"
                    else:
                        with resolved_path.open("r") as f:
                            content = f.readlines()
                        if insert_line < 0 or insert_line > len(content):
                            result = f"Error: insert_line {insert_line} out of range"
                        else:
                            content.insert(insert_line, new_str.rstrip("\n") + "\n")
                            with resolved_path.open("w") as f:
                                f.writelines(content)
                            result = f"Inserted text at line {insert_line} in {resolved_path}"

            elif command == "undo_edit":
                result = (
                    f"Error: Undo functionality not implemented for {resolved_path}"
                )

            else:
                result = f"Error: Unknown command '{command}'"

        except Exception as e:
            result = f"Error during '{command}': {str(e)}"

        if self.traj_logger:
            self.traj_logger.log_step(
                response="",
                thought=f"Perform '{command}' operation on file system.",
                action=f"{self.name}: {command}",
                observation=result,
                query=[{"role": "user", "content": command}],
                state={
                    "repo_path": str(self.environment.repo_path),
                    "target_path": str(resolved_path) if resolved_path else "unknown",
                    "command": command,
                    "duration_seconds": perf_counter() - start,
                },
            )

        return result


# EOF
