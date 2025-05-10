import argparse
import json
import logging
import os
from dotenv import load_dotenv
from rich.logging import RichHandler

from src.agent import AutonomousAgent
from src.config_agent import ConfigAgent
from src.models.environment import Environment
from src.models.preprocess_problem import PreprocessProblem
from src.models.problem import Problem
from src.utils.io_utils import project_root
from src.utils.swe_bench_util import load_swe_bench_verified_by_id

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance_id", type=str, required=True, help="SWE-bench Verified instance ID")
    args = parser.parse_args()

    root_path = project_root()
    root_output = "/Users/coby/TEMP/"
    load_dotenv(dotenv_path=os.path.join(root_path, ".env"))

    # You can filter by instance_id locally or load just one entry
    problem: Problem = load_swe_bench_verified_by_id(instance_id=args.instance_id)
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
    output_path = f"/app/output/{args.instance_id}.json"
    with open(output_path, "w") as f:
        json.dump(response, f, indent=2)

    print(f"[Agent] Output saved to {output_path}")


if __name__ == "__main__":
    main()

