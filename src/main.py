# main.py
import argparse
import logging
import os
import tempfile
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from rich.logging import RichHandler

from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.problem import Problem
from src.utils.io_utils import project_root
from src.utils.swe_bench_util import load_swe_bench_difficulty
from src.workflow.patch_evaluator import PatchEvaluator
from src.workflow.patch_generator import PatchGenerator

logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)


def run(problem: Problem, environment: Environment, config_agent: ConfigAgent):
    generator = PatchGenerator(
        problem=problem, environment=environment, config_agent=config_agent
    )
    evaluator = PatchEvaluator(
        problem=problem, environment=environment, config_agent=config_agent
    )
    patch = generator.generate_patch()
    evaluator.evaluate(patch)


def run_validation(
    problem: Problem, environment: Environment, config_agent: ConfigAgent
):
    evaluator = PatchEvaluator(
        problem=problem, environment=environment, config_agent=config_agent
    )
    evaluator.evaluate(problem.patch)


def main(problems: List[Problem], root_output: Path, root_path: Path):
    for problem in problems:
        environment = Environment(
            problem=problem,
            root_output=root_output,
            root_path=root_path,
        )
        config_agent = ConfigAgent()
        run(problem=problem, environment=environment, config_agent=config_agent)


if __name__ == "__main__":
    try:
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
        problems = problems[2:4]
        main(problems=problems, root_output=root_output, root_path=root_path)
    except Exception as e:
        logging.getLogger("rich").exception(f"[Agent] ❌ Unhandled error: {e}")
        raise

# EOF
