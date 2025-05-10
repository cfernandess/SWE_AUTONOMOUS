# repo_structure.py
from pathlib import Path
from typing import List, Tuple


class RepoStructure:
    """
    Class to generate a tree-like text representation of a repository
    """

    def __init__(self, repo_path: Path, file_ext: List[str]):
        self.repo_path = repo_path
        self.file_ext = file_ext

    def generate_structure(self) -> Tuple[str, List[Path]]:
        """
        Generate the tree-like representation of the repository.

        Returns:
            Tuple[str, List[str]]: Formatted repository structure and list of included file paths.
        """
        return self._generate_structure_recursive(self.repo_path)

    from pathlib import Path
    from typing import Tuple, List

    def _generate_structure_recursive(
        self, current_path: Path, prefix: str = ""
    ) -> Tuple[str, List[Path]]:
        """
        Recursively generates the tree-like structure of the repository,
        including only directories, Python files, and Markdown files, skipping hidden files.

        Args:
            current_path (Path): Current directory path being traversed.
            prefix (str): Prefix for indentation.

        Returns:
            Tuple[str, List[Path]]: Tree-like structure and list of included file paths (as Path objects).
        """
        structure = []
        files = []

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
                        )
                        if subtree_str:
                            structure.append(subtree_str)
                        files.extend(subtree_files)

        except Exception as e:
            structure.append(f"{prefix}Error reading directory: {e}")
            raise

        return "\n".join(structure), files


# EOF
