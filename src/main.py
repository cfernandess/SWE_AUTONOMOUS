# main.py

import argparse
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from rich.logging import RichHandler

from src.agent.agent import AutonomousAgent
from src.config.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.preprocess_problem import PreprocessProblem
from src.models.problem import Problem
from src.utils.io_utils import project_root
from src.utils.swe_bench_util import load_swe_bench

logging.basicConfig(
    level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--instance_id", type=str, required=True, help="SWE-bench Verified instance ID"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run outside Docker (writes to ~/swe_bot_output)",
    )
    args = parser.parse_args()
    if args.local:
        root_output = Path.home() / "swe_bot_output"
        root_path = project_root()
        load_dotenv(dotenv_path=os.path.join(root_path, ".env"))
    else:
        root_output = Path("/app/output")
        root_path = Path("/app")

    root_output.mkdir(parents=True, exist_ok=True)
    problem: Problem = load_swe_bench(
        path="princeton-nlp/SWE-bench_Verified", instance_id=args.instance_id
    )
    if problem is None:
        raise ValueError(f"Instance ID {args.instance_id} not found.")

    environment = Environment(
        instance_id=problem.instance_id,
        root_output=root_output,
        root_path=root_path,
    )
    environment.load_problem(problem)

    agent = AutonomousAgent(
        preprocess_problem=PreprocessProblem(problem=problem),
        environment=environment,
        config_agent=ConfigAgent(),
    )

    response = agent.run()

    output_path = root_output / f"{args.instance_id}.json"
    with open(output_path, "w") as f:
        json.dump(response, f, indent=2)

    environment.logger.info(f"[Agent] ✅ Output saved to {output_path}")


# docker run swe-agent --instance_id=astropy__astropy-12907
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.getLogger("rich").exception(f"[Agent] ❌ Unhandled error: {e}")
        raise

# EOF
