# main.py
import argparse
import logging
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from rich.logging import RichHandler

from src.agent.problem_pipeline import ProblemPipeline
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.utils.io_utils import project_root
from src.utils.swe_bench_util import load_swe_bench_difficulty

logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)


def main():
    p = argparse.ArgumentParser()
    # p.add_argument("--instance_id", required=True)
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
    problem = problems[60]
    environment = Environment(
        problem=problem,
        root_output=root_output,
        root_path=root_path,
    )
    config_agent = ConfigAgent()
    pipeline = ProblemPipeline(
        problem=problem, environment=environment, config_agent=config_agent
    )
    pipeline.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.getLogger("rich").exception(f"[Agent] ❌ Unhandled error: {e}")
        raise

# EOF
