# test_editor_tool.py
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.tools.edit_tool import EditorTool


@pytest.fixture(scope="session", autouse=True)
def ensure_fake_repo_root():
    repo_root = Path("/tmp/fake-repo")
    repo_root.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(repo_root, ignore_errors=True)


@pytest.fixture
def tool():
    mock_problem = MagicMock()
    mock_environment = MagicMock()
    mock_environment.logger = MagicMock()
    mock_environment.traj_logger = MagicMock()
    mock_environment.repo_path = "/tmp/fake-repo"

    mock_config_agent = MagicMock()
    return EditorTool(
        problem=mock_problem,
        environment=mock_environment,
        config_agent=mock_config_agent,
    )


@pytest.fixture
def temp_file():
    repo_root = Path("/tmp/fake-repo")
    path = repo_root / "file.txt"
    path.write_text("line1\nline2\nline3\n")
    yield str(path)
    path.unlink(missing_ok=True)


def test_create_file(tool):
    path = Path("/tmp/fake-repo/new.txt")
    if path.exists():
        path.unlink()
    result = tool.forward(
        command="create",
        path=str(path),
        file_text="hello\nworld",
    )
    assert path.exists()
    assert "File created" in result


def test_view_file_full(tool, temp_file):
    result = tool.forward(command="view", path=temp_file)
    assert "line1" in result
    assert "line2" in result
    assert "1" in result and "2" in result


def test_view_file_range(tool, temp_file):
    result = tool.forward(command="view", path=temp_file, view_range=[2, 3])
    assert "line2" in result
    assert "line1" not in result


def test_str_replace_success(tool, temp_file):
    result = tool.forward(
        command="str_replace",
        path=temp_file,
        old_str="line2",
        new_str="replaced",
    )
    assert "Successfully replaced" in result
    with open(temp_file) as f:
        content = f.read()
        assert "replaced" in content
        assert "line2" not in content


def test_str_replace_fail_not_found(tool, temp_file):
    result = tool.forward(
        command="str_replace",
        path=temp_file,
        old_str="not_found",
        new_str="new",
    )
    assert "Error: old_str not found" in result


def test_str_replace_fail_multiple(tool):
    path = Path("/tmp/fake-repo/dupe.txt")
    path.write_text("repeat\nrepeat\n")
    result = tool.forward(
        command="str_replace",
        path=str(path),
        old_str="repeat",
        new_str="once",
    )
    assert "must be unique" in result
    path.unlink(missing_ok=True)


def test_insert_success(tool, temp_file):
    result = tool.forward(
        command="insert",
        path=temp_file,
        insert_line=1,
        new_str="inserted",
    )
    assert "Inserted text" in result
    with open(temp_file) as f:
        content = f.read()
        assert "inserted" in content


def test_insert_out_of_range(tool, temp_file):
    result = tool.forward(
        command="insert",
        path=temp_file,
        insert_line=100,
        new_str="oops",
    )
    assert "out of range" in result


def test_view_nonexistent(tool):
    path = "/tmp/fake-repo/nonexistent.txt"
    result = tool.forward(command="view", path=path)
    assert "is not a file or directory" in result


def test_undo_not_implemented(tool, temp_file):
    result = tool.forward(command="undo_edit", path=temp_file)
    assert "not implemented" in result


# EOF
