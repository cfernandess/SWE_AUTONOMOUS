# docker_utils.py
import json
import shlex
import subprocess  # nosec B603
from pathlib import Path
from typing import Tuple


def run_command(cmd: str, cwd: Path = None, timeout: int = 120) -> Tuple[str, int]:
    """
    Run a shell command securely and return (stdout + stderr, exit_code)
    """
    try:
        result = subprocess.run(
            shlex.split(cmd),
            cwd=str(cwd) if cwd else None,
            shell=False,  # Safer than shell=True
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=True,
        )  # nosec B603
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired as e:
        return f"[TIMEOUT] Command exceeded {timeout}s:\n{e.stdout}", -1


def apply_patch(patch_text: str, repo_path: Path) -> Tuple[str, int]:
    """
    Apply a unified diff patch to the codebase.
    Expects patch_text to be a JSON string with keys: `path` and `diff`.
    Handles markdown code block formatting like ```json ... ``` if present.
    """
    # Clean markdown block if present
    if patch_text.startswith("```json") or patch_text.startswith("```"):
        patch_text = patch_text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        patch_json = json.loads(patch_text)
        diff_str = patch_json["diff"]
    except Exception as e:
        return f"[ERROR] Invalid patch format: {e}", -1

    return apply_diff(diff_str, repo_path)


def apply_diff(diff_str: str, repo_path: Path) -> Tuple[str, int]:
    patch_file = repo_path / "temp.patch"
    patch_file.write_text(diff_str)

    cmd = ["patch", "-p0", "-i", str(patch_file)]
    result = subprocess.run(
        cmd,
        cwd=str(repo_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    patch_file.unlink(missing_ok=True)
    return result.stdout, result.returncode


def setup_repo(repo_path: Path, base_commit: str) -> None:
    """
    Reset repo to clean state and checkout the base commit.
    """
    cmds = [
        "git reset --hard",
        "git clean -fd",
        f"git checkout {base_commit}",
    ]
    for cmd in cmds:
        out, code = run_command(cmd, cwd=repo_path)
        if code != 0:
            raise RuntimeError(f"[setup_repo] Failed: {cmd}\n{out}")


# EOF
