import json
import subprocess
from pathlib import Path
from typing import Tuple, List


def run_command(cmd: List[str], cwd: Path) -> Tuple[str, int]:
    """
    Runs a command and returns its combined output (stdout + stderr) and exit code.
    """
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return proc.stdout + proc.stderr, proc.returncode


def apply_patch(patch_text: str, repo_path: Path) -> Tuple[str, int]:
    """
    Apply a unified diff patch given as a JSON string with `diff` content.
    Strips markdown formatting if present.
    """
    # Remove Markdown code block formatting if present
    if patch_text.strip().startswith("```"):
        patch_text = (
            patch_text.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

    try:
        patch_obj = json.loads(patch_text)
        diff_str = patch_obj["diff"]
    except Exception as e:
        return f"[ERROR] Invalid patch format: {e}", -1

    return apply_diff(diff_str, repo_path)


def apply_diff(diff_str: str, repo_path: Path) -> Tuple[str, int]:
    """
    Write diff string to a temporary file and apply it using `patch -p0`.
    """
    patch_file = repo_path / "temp.patch"
    patch_file.write_text(diff_str)

    result = subprocess.run(
        ["patch", "-p0", "-i", str(patch_file)],
        cwd=repo_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    patch_file.unlink(missing_ok=True)
    return result.stdout, result.returncode


def setup_repo(repo_path: Path, env_commit: str, base_commit: str) -> None:
    """
    Set up the repo for patch evaluation following SWE-bench parity:
    1. Reset and clean the repo.
    2. Checkout the environment setup commit and install dependencies.
    3. Checkout the base commit to evaluate the patch.
    """
    commands = [
        ["git", "reset", "--hard"],
        ["git", "clean", "-fd"],
        ["git", "checkout", env_commit],
    ]

    for cmd in commands:
        out, code = run_command(cmd, cwd=repo_path)
        if code != 0:
            raise RuntimeError(f"[setup_repo] Failed: {' '.join(cmd)}\n{out}")

    install_dependencies(repo_path)

    out, code = run_command(["git", "checkout", base_commit], cwd=repo_path)
    if code != 0:
        raise RuntimeError(f"[setup_repo] Failed: git checkout {base_commit}\n{out}")


def install_dependencies(repo_path: Path) -> None:
    subprocess.run(
        ["pip", "install", "--upgrade", "pip", "setuptools==65.5.1"], check=True
    )

    # Pin numpy to a version that avoids core API deprecation
    subprocess.run(
        [
            "pip",
            "install",
            "wheel",
            "cython",
            "numpy<2.0",  # <- Avoid np.core deprecation
            "extension-helpers",
            "pyerfa>=2.0",
            "setuptools_scm[toml]",
        ],
        check=True,
    )

    requirements = repo_path / "requirements.txt"
    if requirements.exists():
        subprocess.run(
            ["pip", "install", "-r", str(requirements)], cwd=repo_path, check=True
        )
    elif (repo_path / "pyproject.toml").exists() or (repo_path / "setup.py").exists():
        subprocess.run(
            ["pip", "install", "--no-build-isolation", "."], cwd=repo_path, check=True
        )


# EOF
