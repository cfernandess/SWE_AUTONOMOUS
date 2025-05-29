# enums.py
from enum import Enum


class RESULT(str, Enum):
    ERROR = "ERROR"
    PASSED = "PASSED"
    INIT = "INIT"


class GRAPH_STATE(str, Enum):
    START = "start"
    GENERATE_PATCH = "generate_patch"
    VALIDATE_PATCH = "validate_patch"
    EVALUATE_PATCH = "evaluate_patch"
    END = "end"


# EOF
