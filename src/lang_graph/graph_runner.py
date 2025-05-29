# graph_runner.py

from langgraph.graph import StateGraph, START, END

from src.config.config_agent import ConfigAgent
from src.lang_graph.evaluate_patch_node import (
    make_evaluate_patch_node,
    route_from_evaluation,
)
from src.lang_graph.generate_patch_node import make_generate_patch_node
from src.lang_graph.patch_state import PatchState
from src.lang_graph.validate_patch_node import (
    make_validate_patch_node,
    route_from_validation,
)
from src.models.enums import GRAPH_STATE
from src.models.environment import Environment
from src.models.problem import Problem


def build_patch_graph(
    problem: Problem, environment: Environment, config_agent: ConfigAgent
):
    graph = StateGraph(PatchState)

    # Add nodes using enum values
    graph.add_node(
        GRAPH_STATE.GENERATE_PATCH,
        make_generate_patch_node(problem, environment, config_agent),
    )
    graph.add_node(
        GRAPH_STATE.VALIDATE_PATCH,
        make_validate_patch_node(problem, environment, config_agent),
    )
    graph.add_node(
        GRAPH_STATE.EVALUATE_PATCH,
        make_evaluate_patch_node(problem, environment, config_agent),
    )

    graph.add_edge(START, GRAPH_STATE.GENERATE_PATCH)
    graph.add_edge(GRAPH_STATE.GENERATE_PATCH, GRAPH_STATE.VALIDATE_PATCH)

    graph.add_conditional_edges(
        GRAPH_STATE.VALIDATE_PATCH,
        route_from_validation,
        {
            GRAPH_STATE.GENERATE_PATCH: GRAPH_STATE.GENERATE_PATCH,
            GRAPH_STATE.EVALUATE_PATCH: GRAPH_STATE.EVALUATE_PATCH,
            END: END,
        },
    )

    graph.add_conditional_edges(
        GRAPH_STATE.EVALUATE_PATCH,
        route_from_evaluation,
        {
            GRAPH_STATE.GENERATE_PATCH: GRAPH_STATE.GENERATE_PATCH,
            END: END,
        },
    )

    return graph.compile()


# EOF
