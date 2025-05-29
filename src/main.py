# main.py
import argparse
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.tracers.context import tracing_v2_enabled
from rich.logging import RichHandler

from src.config.config_agent import ConfigAgent
from src.config.config_model import ConfigModel
from src.lang_graph.graph_runner import build_patch_graph
from src.lang_graph.patch_state import make_initial_patch_state
from src.models.environment import Environment
from src.models.problem import Problem
from src.tools.patch_validator_tool import PatchValidatorTool
from src.utils.io_utils import project_root
from src.utils.swe_bench_util import load_swe_bench_difficulty
from src.workflow.patch_evaluator import PatchEvaluator
from src.workflow.patch_generator import PatchGenerator

logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)


def run_graph(problem: Problem, environment: Environment):
    try:
        config_model_openai = ConfigModel(model_name="gpt-4o", vendor_name="openai")
        # config_model_anthropic = ConfigModel(model_name="claude-3-7-sonnet-20250219", vendor_name="anthropic")
        config_agent = ConfigAgent(
            config_model=config_model_openai,
            patch_prompt_path="src/prompts/patch_lg.prompt",
        )
        graph = build_patch_graph(
            problem=problem, environment=environment, config_agent=config_agent
        )
        initial_state = make_initial_patch_state()
        initial_state["gold_patch"] = problem.patch
        with tracing_v2_enabled(project_name="SWE"):
            result = graph.invoke(input=initial_state)
            print(result)
    except Exception as e:
        logging.getLogger("rich").exception(f"[Agent] ❌ Unhandled error: {e}")
        raise


def run(problem: Problem, environment: Environment):
    try:
        config_model_openai = ConfigModel(model_name="gpt-4o", vendor_name="openai")
        # config_model_anthropic = ConfigModel(model_name="claude-3-7-sonnet-20250219", vendor_name="anthropic")
        config_agent = ConfigAgent(config_model=config_model_openai)
        generator = PatchGenerator(
            problem=problem, environment=environment, config_agent=config_agent
        )
        evaluator = PatchEvaluator(
            problem=problem, environment=environment, config_agent=config_agent
        )
        patch = generator.generate_patch()
        evaluator.evaluate(patch)
        print(patch)
    except Exception as e:
        logging.getLogger("rich").exception(f"[Agent] ❌ Unhandled error: {e}")
        raise


def validate_patch_on_problem(
    problem: Problem, environment: Environment, config_agent: ConfigAgent
):
    patch = problem.patch
    tool = PatchValidatorTool(problem, environment, config_agent)
    result = tool.forward(patch)
    print(result)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--local", action="store_true")
    args = p.parse_args()
    if args.local:
        root_output = Path("/Users/coby/TEMP")
    else:
        root_output = Path(tempfile.mkdtemp(prefix="swe_"))
    root_path = project_root() if args.local else Path("/app")
    root_output.mkdir(parents=True, exist_ok=True)
    if args.local:
        load_dotenv(os.path.join(root_path, ".env"))
    problems = load_swe_bench_difficulty()
    problems = [problems[10]]
    for problem in problems:
        environment = Environment(
            problem=problem,
            root_output=root_output,
            root_path=root_path,
        )
        run_graph(problem=problem, environment=environment)

# EOF
