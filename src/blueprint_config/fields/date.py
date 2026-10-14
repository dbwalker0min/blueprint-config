from __future__ import annotations

import datetime as dt
from typing import Any

from ..diagnostic import Diagnostics
from ..items import FieldItem
from ..types import MISSING, Missing, ParamTypeChk
from .input_section import InputSection


class Date(FieldItem):
    """A date input, converted to a Python date.

    Defaults accept strings or Python values and are emitted as ISO strings.
    Invalid declarations and runtime values accumulate diagnostics.
    Missing/None values use the default, then allow_none. No timezone is inferred.
    """

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [ParamTypeChk("default", (str, dt.date), MISSING)]
    )

    def __init__(
        self,
        *args: Any,
        name: str = "",
        description: str = "",
        default: str | dt.date | Missing = MISSING,
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
    def _parse(value: str | dt.date) -> dt.date:
        if isinstance(value, str):
            if len(value) != 10 or value[4] != "-" or value[7] != "-":
                raise ValueError("Date requires YYYY-MM-DD")
            return dt.date.fromisoformat(value)
        if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
            return value
        raise TypeError(f"Value of Date is not a date or string {value!r}")

    def convert(
        self, value: str | dt.date | None, diag: Diagnostics
    ) -> dt.date | None | Missing:
        value = self._resolve_none(value, diag)
        if value is MISSING or value is None:
            return value
        try:
            return self._parse(value)
        except (TypeError, ValueError) as exc:
            diag.error(str(exc))
            return MISSING

    def selector(self) -> dict[str, Any]:
        return {"date": {}}
