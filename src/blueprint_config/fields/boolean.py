from __future__ import annotations

from typing import Any

from ..diagnostic import Diagnostics
from ..items import FieldItem, InputSection
from ..types import MISSING, Missing, ParamTypeChk


class Boolean(FieldItem):
    """A toggle input. Arguments are checked when its configuration class is built.

    Unknown keywords raise TypeError at construction. A missing/None runtime value
    uses the declared default, then allow_none; explicit False is preserved.
    """

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [ParamTypeChk("default", bool, MISSING)]
    )

    def __init__(
        self,
        *,
        name: str = "",
        description: str = "",
        default: bool | Missing = MISSING,
        allow_none: bool = False,
        section: InputSection | None = None,
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            default=default,
            allow_none=allow_none,
            **({"section": section} if section is not None else {}),
        )

    def convert(self, value: bool | None, diag: Diagnostics) -> bool | None:
        value = self._resolve_none(value, diag)
        if value is None or isinstance(value, bool):
            return value
        raise TypeError(f"Value of Boolean is not boolean or None {value!r}")

    def selector(self) -> dict[str, Any]:
        return {"boolean": {}}
