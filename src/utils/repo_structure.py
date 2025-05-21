# repo_structure.py
from pathlib import Path
from typing import List, Tuple, Optional


class RepoStructure:
    """
    Class to generate a tree-like text representation of a repository
    with optional max depth for traversal.
    """

    def __init__(
        self, repo_path: Path, file_ext: List[str], max_depth: Optional[int] = 1
    ):
        self.repo_path = repo_path
        self.file_ext = file_ext
        self.max_depth = max_depth

    def generate_structure(self) -> Tuple[str, List[Path]]:
        """
        Generate the tree-like representation of the repository.

        Returns:
            Tuple[str, List[Path]]: Formatted repository structure and list of included file paths.
        """
        return self._generate_structure_recursive(self.repo_path, depth=0)

    def _generate_structure_recursive(
        self, current_path: Path, prefix: str = "", depth: int = 0
    ) -> Tuple[str, List[Path]]:
        """
        Recursively generates the tree-like structure of the repository.

        Args:
            current_path (Path): Current directory path being traversed.
            prefix (str): Prefix for indentation.
            depth (int): Current depth of recursion.

        Returns:
            Tuple[str, List[Path]]: Tree-like structure and list of included file paths.
        """
        structure = []
        files = []

        if self.max_depth is not None and depth > self.max_depth:
            return "", []

        try:
            entries = sorted(current_path.iterdir(), key=lambda p: p.name)

            for idx, entry in enumerate(entries):
                if entry.name.startswith("."):
                    continue

                relative_path = entry.relative_to(self.repo_path)

                if entry.is_dir() or entry.suffix in self.file_ext:
                    connector = "├── " if idx < len(entries) - 1 else "└── "
                    structure.append(f"{prefix}{connector}{entry.name}")

                    if entry.is_file() and entry.suffix in self.file_ext:
                        files.append(relative_path)

                    if entry.is_dir():
                        subtree_str, subtree_files = self._generate_structure_recursive(
                            entry,
                            prefix + ("│   " if idx < len(entries) - 1 else "    "),
                            depth=depth + 1,
                        )
                        if subtree_str:
                            structure.append(subtree_str)
                        files.extend(subtree_files)

        except Exception as e:
            structure.append(f"{prefix}Error reading directory: {e}")
            raise

        return "\n".join(structure), files


# EOF
