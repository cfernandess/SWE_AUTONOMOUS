import os

from smolagents.tools import Tool


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
        try:
            if not os.path.isabs(path):
                return f"Error: Path must be absolute: {path}"
            if ".." in os.path.relpath(path, start="/"):
                return f"Error: Path traversal not allowed: {path}"

            if command == "view":
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
                    return "\n".join(files)
                elif os.path.isfile(path):
                    with open(path, "r") as f:
                        content = f.readlines()
                    if view_range:
                        start = max(0, view_range[0] - 1)
                        end = view_range[1] if view_range[1] != -1 else len(content)
                        content = content[start:end]
                    return "".join(
                        [f"{i + 1:4d} {line}" for i, line in enumerate(content)]
                    )
                else:
                    return f"Error: {path} is not a file or directory."

            elif command == "create":
                if os.path.exists(path):
                    return f"Error: {path} already exists."
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w") as f:
                    f.write(file_text)
                return f"File created: {path}"

            elif command == "str_replace":
                if not os.path.isfile(path):
                    return f"Error: File does not exist: {path}"
                with open(path, "r") as f:
                    content = f.read()
                occurrences = content.count(old_str)
                if occurrences == 0:
                    return f"Error: old_str not found in {path}"
                if occurrences > 1:
                    return f"Error: old_str appears {occurrences} times, must be unique"
                with open(path, "w") as f:
                    f.write(content.replace(old_str, new_str))
                return f"Successfully replaced content in {path}"

            elif command == "insert":
                if not os.path.isfile(path):
                    return f"Error: File does not exist: {path}"
                try:
                    insert_line = int(insert_line)
                except ValueError:
                    return "Error: insert_line must be an integer"
                with open(path, "r") as f:
                    content = f.readlines()
                if insert_line < 0 or insert_line > len(content):
                    return f"Error: insert_line {insert_line} out of range"
                content.insert(insert_line, new_str.rstrip("\n") + "\n")
                with open(path, "w") as f:
                    f.writelines(content)
                return f"Inserted text at line {insert_line} in {path}"

            elif command == "undo_edit":
                return f"Error: Undo functionality not implemented for {path}"

            return f"Error: Unknown command '{command}'"
        except Exception as e:
            return f"Error during '{command}': {str(e)}"
