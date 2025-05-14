from pathlib import Path

import pytest

from src.agent.prompt_template import PromptTemplate
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.preprocess_problem import PreprocessProblem
from src.models.problem import Problem
from src.models.prompt_arg import PromptArg


@pytest.fixture(scope="session")
def dummy_problem():
    yaml_path = Path(__file__).parent.parent / "tests/data/problem.yaml"
    return Problem.from_yaml_file(yaml_path)


@pytest.fixture
def mock_environment(tmp_path):
    return Environment(instance_id="mock", root_output=tmp_path, root_path=tmp_path)


@pytest.fixture
def mock_config_agent():
    config = ConfigAgent()
    config.config_model.model_name = "gpt-4"
    return config


@pytest.fixture
def temp_prompt_file(tmp_path) -> Path:
    path = tmp_path / "test.prompt"
    content = "Hello, $user! Your task is to $task."
    path.write_text(content)
    return path


def test_prompt_substitution_and_token_count(
    dummy_problem,
    mock_environment,
    mock_config_agent,
    temp_prompt_file,
):
    args = [
        PromptArg(name="user", data="Coby"),
        PromptArg(name="task", data="run a test"),
    ]
    prompt = PromptTemplate(
        problem=dummy_problem,
        environment=mock_environment,
        config_agent=mock_config_agent,
        path=temp_prompt_file,
        prompt_args=args,
    )
    result = prompt.generate()
    assert "Coby" in result
    assert "run a test" in result
    assert "$user" not in result
    assert "$task" not in result
    assert result.strip().startswith("Hello, Coby!")


def test_missing_variable_raises_key_error(
    dummy_problem, mock_environment, mock_config_agent, temp_prompt_file
):
    # Provide only one arg, but the template expects two
    args = [PromptArg(name="user", data="Coby")]
    prompt = PromptTemplate(
        problem=dummy_problem,
        environment=mock_environment,
        config_agent=mock_config_agent,
        path=temp_prompt_file,
        prompt_args=args,
    )
    with pytest.raises(KeyError):
        prompt.generate()


def test_non_str_data_raises_type_error(
    dummy_problem, mock_environment, mock_config_agent, temp_prompt_file
):
    with pytest.raises(Exception):
        args = [
            PromptArg(name="user", data="ok"),
            PromptArg(name="task", data="run test"),
        ]
        args[1].data = 123  # Inject invalid type after init

        prompt = PromptTemplate(
            problem=dummy_problem,
            environment=mock_environment,
            config_agent=mock_config_agent,
            path=temp_prompt_file,
            prompt_args=args,
        )
        prompt.generate()
