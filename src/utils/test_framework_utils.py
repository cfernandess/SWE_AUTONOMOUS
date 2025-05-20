# test_framework_utils.py
import os
import subprocess
from enum import Enum
from pathlib import Path


class TestFramework(str, Enum):
    PYTEST = "pytest"
    UNITTEST = "unittest"
    TOX = "tox"
    NO_TESTS = "none"


class TestFrameworkUtils:
    TEST_COMMANDS = {
        TestFramework.PYTEST: "pytest -q",
        TestFramework.UNITTEST: "python -m unittest discover",
        TestFramework.TOX: "tox",
        TestFramework.NO_TESTS: "",
    }

    @staticmethod
    def get_test_command(framework: TestFramework) -> str:
        try:
            return TestFrameworkUtils.TEST_COMMANDS[framework]
        except KeyError:
            raise ValueError(f"Unsupported test framework: {framework}")

    @staticmethod
    def detect_test_framework(repo_path: Path) -> TestFramework:
        tox_path = repo_path / "tox.ini"
        if tox_path.exists():
            try:
                result = subprocess.run(
                    ["tox", "-l"],
                    cwd=str(repo_path),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if result.returncode == 0:
                    return TestFramework.TOX
            except subprocess.CalledProcessError as e:
                print("[detect_test_framework] ⚠️ Invalid tox.ini:", e.stdout.strip())
            except FileNotFoundError:
                print("[detect_test_framework] ❌ 'tox' is not installed")

        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    try:
                        with open(
                            os.path.join(root, file), encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()
                            if "pytest" in content:
                                return TestFramework.PYTEST
                            if "unittest" in content:
                                return TestFramework.UNITTEST
                    except Exception as e:
                        print(f"[detect_test_framework] ⚠️ Failed to read {file}: {e}")

        return TestFramework.NO_TESTS
