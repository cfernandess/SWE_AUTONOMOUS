# io_utils.py
from io import StringIO
import pathspec
from unidiff import PatchSet
import os
import subprocess  # nosec B603
from pathlib import Path
from shutil import which
import logging
from typing import Optional


def apply_patch_to_file(original_content: str, unified_diff: str, filename: str) -> str:
    patch = PatchSet(StringIO(unified_diff))

    for patched_file in patch:
        if patched_file.path == filename or patched_file.target_file.endswith(filename):
            break
    else:
        raise ValueError(f"No matching patch found for {filename}")

    original_lines = original_content.splitlines(keepends=True)
    output_lines = []
    orig_idx = 0

    for hunk in patched_file:
        hunk_start = hunk.source_start - 1
        while orig_idx < hunk_start:
            output_lines.append(original_lines[orig_idx])
            orig_idx += 1

        for line in hunk:
            if line.is_context:
                output_lines.append(original_lines[orig_idx])
                orig_idx += 1
            elif line.is_removed:
                orig_idx += 1
            elif line.is_added:
                output_lines.append(line.value)

    output_lines.extend(original_lines[orig_idx:])
    return "".join(output_lines)


def project_root(marker=".git") -> str:
    try:
        result = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,  # suppress error output
            text=True,
        ).strip()
        if result:
            return result
    except subprocess.CalledProcessError:
        pass  # Git command failed, fallback to filesystem traversal

    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / marker).exists():
            return str(current)
        current = current.parent
    raise FileNotFoundError(f"Could not find project root with marker '{marker}'")


def clone_repo(
        instance_id: str,
        repo: str,
        base_commit: str,
        target_folder: Path,
        logger: Optional[logging.Logger] = None,
) -> Path:
    """
    Clones the repository from GitHub and checks out a specific commit.

    Args:
        instance_id (str): Unique ID for the problem instance.
        repo (str): GitHub repo name (e.g., "astropy/astropy").
        base_commit (str): Git commit to checkout.
        target_folder (Path): Where the repo should be cloned.
        logger (Optional[Logger]): Logger instance for output.

    Returns:
        Path: Path to the checked-out repo.
    """
    logger = logger or logging.getLogger("rich")
    repo_path = target_folder / instance_id

    # ✅ If already cloned and on correct commit
    if repo_path.exists():
        git_dir = repo_path / ".git"
        if git_dir.exists():
            try:
                current_commit = subprocess.check_output(
                    ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                    text=True,
                ).strip()
                if current_commit == base_commit:
                    logger.info(f"[clone_repo] ✅ Repo already at {base_commit}.")
                    return repo_path
                else:
                    logger.warning(f"[clone_repo] ⚠️ Wrong commit ({current_commit} ≠ {base_commit}). Re-cloning...")
                    subprocess.run(["rm", "-rf", str(repo_path)], check=True)  # nosec B603
            except subprocess.SubprocessError:
                logger.warning(f"[clone_repo] ⚠️ Invalid .git repo. Re-cloning...")
                subprocess.run(["rm", "-rf", str(repo_path)], check=True)  # nosec B603

    os.makedirs(repo_path.parent, exist_ok=True)

    if not which("git"):
        raise EnvironmentError("Git is not installed or not found in PATH.")

    repo_url = f"https://github.com/{repo}.git"
    logger.info(f"[clone_repo] Cloning {repo_url} into {repo_path}")

    result = subprocess.run(["git", "clone", repo_url, str(repo_path)], check=False)  # nosec B603
    if result.returncode != 0:
        raise RuntimeError(f"Failed to clone repository: {repo_url}")

    result = subprocess.run(["git", "-C", str(repo_path), "checkout", base_commit], check=False)  # nosec B603
    if result.returncode != 0:
        raise RuntimeError(f"Failed to checkout commit {base_commit}")

    logger.info(f"[clone_repo] ✅ Repo ready at commit {base_commit}")
    return repo_path


def load_file_content(file_path: Path) -> str:
    """
    Loads the full content of a file from disk given its absolute path.
    Args:
        file_path (str): Absolute path to the file.
    Returns:
        str: Entire file content as a single string.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Failed to read file {file_path}: {e}")
        return ""


def read_lines(file_path: str) -> list[str]:
    """
    Reads a file and returns all lines exactly as they are, including blank lines and trailing newlines.

    Args:
        file_path (str): The full path to the file.

    Returns:
        List[str]: A list of all lines from the file (including blank lines and newlines).
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.readlines()
        except Exception as e:
            print(f"Failed to read file {file_path}: {e}")
    return ["N/A"]


def load_gitignore_spec() -> pathspec.PathSpec:
    root_dir = project_root()
    gitignore_path = Path(root_dir) / ".gitignore"
    if not gitignore_path.exists():
        return pathspec.PathSpec.from_lines("gitwildmatch", [])
    with gitignore_path.open() as f:
        lines = f.readlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def annotate_python_files():
    """
    Adds `# filename.py` at the top and `# EOF` at the bottom of each Python file,
    skipping files listed in `.gitignore` and `__init__.py`.
    """
    root_dir = project_root()
    spec = load_gitignore_spec()
    root = Path(root_dir)

    for file_path in root.rglob("*.py"):
        rel_path = file_path.relative_to(root)
        if file_path.name == "__init__.py" or spec.match_file(str(rel_path)):
            continue

        content = file_path.read_text(encoding="utf-8").splitlines()
        already_has_header = content and content[0].strip() == f"# {file_path.name}"
        already_has_footer = content and content[-1].strip() == "# EOF"
        if already_has_header and already_has_footer:
            continue

        new_lines = []
        if not already_has_header:
            new_lines.append(f"# {file_path.name}")
        new_lines.extend(content)
        if content and not already_has_footer:
            new_lines.append("# EOF")

        file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

# EOF
