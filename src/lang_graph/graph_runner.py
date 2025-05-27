# graph_runner.py
import argparse
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_core.tracers.context import tracing_v2_enabled
from src.lang_graph.patch_state import PatchState
from src.models.problem import Problem
from src.models.environment import Environment
from src.config.config_agent import ConfigAgent
from src.utils.io_utils import project_root
from src.utils.swe_bench_util import load_swe_bench_difficulty
from src.lang_graph.graph_nodes import route_from_validation
from src.workflow.patch_generator import PatchGenerator
from src.lang_graph.generate_patch_node import make_generate_patch_node
from src.lang_graph.validate_patch_node import make_validate_patch_node
from src.lang_graph.evaluate_patch_node import make_evaluate_patch_node


def build_patch_graph(
    problem: Problem, environment: Environment, config_agent: ConfigAgent
):
    generator = PatchGenerator(
        problem=problem, environment=environment, config_agent=config_agent
    )

    graph = StateGraph(PatchState)

    graph.add_node("generate_patch", make_generate_patch_node(generator))
    graph.add_node(
        "validate_patch", make_validate_patch_node(problem, environment, config_agent)
    )
    graph.add_node(
        "evaluate_patch", make_evaluate_patch_node(problem, environment, config_agent)
    )

    graph.add_edge(START, "generate_patch")
    graph.add_edge("generate_patch", "validate_patch")
    graph.add_conditional_edges(
        "validate_patch",
        route_from_validation,
        {
            "generate_patch": "generate_patch",
            "evaluate_patch": "evaluate_patch",
        },
    )
    graph.add_edge("evaluate_patch", END)

    return graph.compile()


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
    problem = problems[22]
    environment = Environment(
        problem=problem, root_output=root_output, root_path=root_path
    )
    config_agent = ConfigAgent()
    graph = build_patch_graph(
        problem=problem, environment=environment, config_agent=config_agent
    )

    initial_state = {"attempts": 0}

    with tracing_v2_enabled(project_name="SWE"):
        result = graph.invoke(input=initial_state)
        print(result)

# EOF
