# generate_patch_node.py
from langchain_core.runnables import RunnableLambda
from src.workflow.patch_generator import PatchGenerator
from src.lang_graph.patch_state import PatchState


def make_generate_patch_node(generator: PatchGenerator):
    def generate_patch(state: PatchState) -> PatchState:
        patch_str = generator.generate_patch()
        return {
            **state,
            "patch": patch_str,
            "attempts": state.get("attempts", 0) + 1,
        }

    return RunnableLambda(generate_patch).with_config({"run_name": "generate_patch"})


# EOF
