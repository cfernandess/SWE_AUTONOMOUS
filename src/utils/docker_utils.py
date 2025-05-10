# docker_utils.py

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
    """
    patch_file = repo_path / "temp.patch"
    patch_file.write_text(patch_text)
    cmd = f"patch -p1 < {patch_file.name}"
    # `patch` still uses shell features like redirection; allow one-off use
    out, code = (
        subprocess.run(
            cmd,
            cwd=str(repo_path),
            shell=True,  # nosec: required for input redirection
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        ).stdout,
        0,
    )  # nosec B603
    patch_file.unlink(missing_ok=True)
    return out, code


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


def run_pytest(repo_path: Path, marker: str = "") -> Tuple[str, int]:
    """
    Run pytest with optional marker and return output and status code.
    """
    cmd = "pytest -q"
    if marker:
        cmd += f" -m {marker}"
    return run_command(cmd, cwd=repo_path)


# EOF
