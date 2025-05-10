import pytest
from src.tools.bash_tool import BashTool


@pytest.fixture
def tool():
    return BashTool()


def test_simple_echo(tool):
    result = tool.forward("echo Hello")
    assert "Hello" in result
    assert "STDOUT:" in result
    assert "STDERR:" in result


def test_invalid_command(tool):
    result = tool.forward("invalid_command_xyz")
    assert "STDOUT:" in result
    assert "STDERR:" in result
    assert "ERROR:" in result
    assert "invalid_command_xyz" in result  # error message must mention command
    assert "No such file or directory" in result or "not found" in result


def test_command_timeout(tool, monkeypatch):
    # Simulate long-running command by monkeypatching subprocess
    import subprocess

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs.get("timeout", 30))

    monkeypatch.setattr("subprocess.run", fake_run)
    result = tool.forward("sleep 60")
    assert "timed out" in result.lower()


def test_command_exception(tool, monkeypatch):
    # Simulate a generic exception
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: 1 / 0)
    result = tool.forward("echo test")
    assert "STDOUT:" in result
    assert "STDERR:" in result
    assert "ERROR:" in result
    assert "division by zero" in result
