# main.py
import argparse
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

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


def run_graph(problem: Problem, environment: Environment) -> dict[str, Any]:
    try:
        # config_model_openai = ConfigModel(model_name="gpt-4o", vendor_name="openai")
        config_model_anthropic = ConfigModel(
            model_name="claude-3-7-sonnet-20250219", vendor_name="anthropic"
        )
        config_agent = ConfigAgent(config_model=config_model_anthropic)
        graph = build_patch_graph(
            problem=problem, environment=environment, config_agent=config_agent
        )
        initial_state = make_initial_patch_state()
        initial_state["gold_patch"] = problem.patch
        with tracing_v2_enabled(project_name="SWE"):
            result = graph.invoke(input=initial_state)
        return result

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
    resolved_count = 0
    total = 0
    for problem in problems[0:1]:
        environment = Environment(
            problem=problem,
            root_output=root_output,
            root_path=root_path,
        )
        result = run_graph(problem=problem, environment=environment)

        # Extract result flag
        is_resolved = result.get("evaluation_report", {}).get("resolved", False)
        resolved_count += int(is_resolved)
        total += 1
        status_icon = "✅" if is_resolved else "❌"
        print(f"{status_icon} {problem.instance_id} - Resolved: {is_resolved}")

    print("\n🔢 Accuracy Report")
    print(f"Resolved: {resolved_count}/{total}")
    print(f"Accuracy: {resolved_count / total:.2%}")

# EOF
