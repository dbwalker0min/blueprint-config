from __future__ import annotations

import datetime as dt
from typing import Any

from ..diagnostic import Diagnostics
from ..items import FieldItem
from ..types import MISSING, Missing, ParamTypeChk
from .input_section import InputSection


class Time(FieldItem):
    """A time input with accumulating diagnostics and ISO string defaults."""

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [ParamTypeChk("default", (str, dt.time), MISSING)]
    )

    def __init__(
        self,
        *args: Any,
        name: str = "",
        description: str = "",
        default: str | dt.time | Missing = MISSING,
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

    def validate(self, parent, field_name: str, diag: Diagnostics | None):
        super().validate(parent, field_name, diag)
        assert diag is not None
        if self.default is not MISSING:
            try:
                parsed = self._parse(self.default)
            except (TypeError, ValueError) as exc:
                diag.error(f"From field {field_name}: invalid default: {exc}")
                self.default = MISSING
            else:
                self.default = parsed.isoformat()

    @staticmethod
    def _parse(value: str | dt.time) -> dt.time:
        if isinstance(value, str):
            return dt.time.fromisoformat(value)
        if isinstance(value, dt.time):
            return value
        raise TypeError(f"Value of Time is not a time or string {value!r}")

    def convert(
        self, value: str | dt.time | None, diag: Diagnostics
    ) -> dt.time | None | Missing:
        value = self._resolve_none(value, diag)
        if value is MISSING or value is None:
            return value
        try:
            return self._parse(value)
        except (TypeError, ValueError) as exc:
            diag.error(str(exc))
            return MISSING

    def selector(self) -> dict:
        return {"time": {}}
