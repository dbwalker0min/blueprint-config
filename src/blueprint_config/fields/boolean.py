from __future__ import annotations

from typing import Any

from ..diagnostic import Diagnostics
from ..items import FieldItem
from ..types import MISSING, Missing, ParamTypeChk
from .input_section import InputSection


class Boolean(FieldItem):
    """A toggle input. Arguments are checked when its configuration class is built.

    Unsupported arguments become build errors. A missing/None runtime value
    uses the declared default, then allow_none; explicit False is preserved.
    """

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [ParamTypeChk("default", bool, MISSING)]
    )

    def __init__(
        self,
        *args: Any,
        name: str = "",
        description: str = "",
        default: bool | Missing = MISSING,
        allow_none: bool = False,
        section: InputSection | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            *args,
            name=name,
            description=description,
            default=default,
            allow_none=allow_none,
            **({"section": section} if section is not None else {}),
            **kwargs,
        )

    def convert(self, value: bool | None, diag: Diagnostics) -> bool | None | Missing:
        value = self._resolve_none(value, diag)
        if value is MISSING or value is None or isinstance(value, bool):
            return value
        diag.error(f"Value of Boolean is not boolean or None {value!r}")
        return MISSING

    def selector(self) -> dict[str, Any]:
        return {"boolean": {}}
