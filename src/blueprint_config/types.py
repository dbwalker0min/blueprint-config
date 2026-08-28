from enum import Enum, auto
from typing import Any, NamedTuple


class _Missing:
    """This is a sentinel value to indicate that a field has no default value"""

    __slots__ = ()

    def __repr__(self):
        return "MISSING"


class Status(Enum):
    """This makes the status of a return code explicit."""
    VALID = auto()
    INVALID = auto()


MISSING = _Missing()

class ParamTypeChk(NamedTuple):
    param: str
    exp_type: type
    default: Any
