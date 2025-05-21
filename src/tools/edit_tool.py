# edit_tool.py
import os
from time import perf_counter

from smolagents.tools import Tool

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem


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
        "path": {"type": "string", "description": "Absolute path to file or directory"},
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

        try:
            if not os.path.isabs(path):
                result = f"Error: Path must be absolute: {path}"
            elif ".." in os.path.relpath(path, start="/"):
                result = f"Error: Path traversal not allowed: {path}"

            elif command == "view":
                if os.path.isdir(path):
                    files = []
                    for root, _, filenames in os.walk(path, topdown=True):
                        level = root.replace(path, "").count(os.sep)
                        if level <= 2:
                            indent = " " * 4 * level
                            files.append(f"{indent}{os.path.basename(root)}/")
                            subindent = " " * 4 * (level + 1)
                            for f in filenames:
                                if not f.startswith("."):
                                    files.append(f"{subindent}{f}")
                    result = "\n".join(files)
                elif os.path.isfile(path):
                    with open(path, "r") as f:
                        content = f.readlines()
                    if view_range:
                        start_line = max(0, view_range[0] - 1)
                        end_line = (
                            view_range[1] if view_range[1] != -1 else len(content)
                        )
                        content = content[start_line:end_line]
                    result = "".join(
                        [f"{i + 1:4d} {line}" for i, line in enumerate(content)]
                    )
                else:
                    result = f"Error: {path} is not a file or directory."

            elif command == "create":
                if os.path.exists(path):
                    result = f"Error: {path} already exists."
                else:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w") as f:
                        f.write(file_text)
                    result = f"File created: {path}"

            elif command == "str_replace":
                if not os.path.isfile(path):
                    result = f"Error: File does not exist: {path}"
                else:
                    with open(path, "r") as f:
                        content = f.read()
                    occurrences = content.count(old_str)
                    if occurrences == 0:
                        result = f"Error: old_str not found in {path}"
                    elif occurrences > 1:
                        result = f"Error: old_str appears {occurrences} times, must be unique"
                    else:
                        with open(path, "w") as f:
                            f.write(content.replace(old_str, new_str))
                        result = f"Successfully replaced content in {path}"

            elif command == "insert":
                if not os.path.isfile(path):
                    result = f"Error: File does not exist: {path}"
                else:
                    try:
                        insert_line = int(insert_line)
                    except ValueError:
                        result = "Error: insert_line must be an integer"
                    else:
                        with open(path, "r") as f:
                            content = f.readlines()
                        if insert_line < 0 or insert_line > len(content):
                            result = f"Error: insert_line {insert_line} out of range"
                        else:
                            content.insert(insert_line, new_str.rstrip("\n") + "\n")
                            with open(path, "w") as f:
                                f.writelines(content)
                            result = f"Inserted text at line {insert_line} in {path}"

            elif command == "undo_edit":
                result = f"Error: Undo functionality not implemented for {path}"

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
                    "target_path": str(path),
                    "command": command,
                    "duration_seconds": perf_counter() - start,
                },
            )

        return result


# EOF
