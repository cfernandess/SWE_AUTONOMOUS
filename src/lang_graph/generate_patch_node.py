# generate_patch_node.py
from langchain_core.runnables import RunnableLambda

from src.config.config_agent import ConfigAgent
from src.lang_graph.patch_state import PatchState
from src.models.enums import GRAPH_STATE
from src.models.environment import Environment
from src.models.problem import Problem
from src.workflow.patch_generator_lg import PatchGeneratorLG


def make_generate_patch_node(
    problem: Problem,
    environment: Environment,
    config_agent: ConfigAgent,
):
    generator = PatchGeneratorLG(
        problem=problem,
        environment=environment,
        config_agent=config_agent,
    )

    def generate_patch(state: PatchState) -> PatchState:
        patch_str = generator.generate_patch(state)
        attempts = state.get("generation_attempts", 0) + 1

        return {
            **state,
            "patch": patch_str,
            "generation_attempts": attempts,
            "graph_state": GRAPH_STATE.GENERATE_PATCH,
        }

    return RunnableLambda(generate_patch).with_config({"run_name": "generate_patch"})


# EOF
