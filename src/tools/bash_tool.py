import shlex
import subprocess

from smolagents.tools import Tool


class BashTool(Tool):
    name = "bash"
    description = """Run commands in a bash shell.\n
* State is persistent across command calls and discussions with the user.\n
* You can use sed to inspect file ranges, e.g., 'sed -n 10,25p /path/file.py'.\n
* Long outputs may be truncated.\n
* You can use `ruff` directly to lint or fix Python files — e.g., `ruff check file.py` or `ruff check --fix file.py`.\n
* This is the preferred way to perform linting and auto-fixing of code.\n
"""
    inputs = {
        "command": {
            "type": "string",
            "description": "The bash command to run (single line, no pipes or redirects).",
        }
    }
    output_type = "string"

    def forward(self, command: str) -> str:
        try:
            # Safely split the command into list form
            command_list = shlex.split(command)
            result = subprocess.run(
                command_list, capture_output=True, text=True, timeout=30
            )  # nosec B603
            return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"
