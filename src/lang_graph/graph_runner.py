# graph_runner.py

from langgraph.graph import StateGraph, START, END

from src.config.config_agent import ConfigAgent
from src.lang_graph.evaluate_patch_node import make_evaluate_patch_node
from src.lang_graph.generate_patch_node import make_generate_patch_node
from src.lang_graph.patch_state import PatchState
from src.lang_graph.validate_patch_node import make_validate_patch_node
from src.lang_graph.validate_patch_node import route_from_validation
from src.models.environment import Environment
from src.models.problem import Problem
from src.workflow.patch_generator import PatchGenerator


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


# EOF
