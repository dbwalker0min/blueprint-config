from __future__ import annotations

import datetime as dt
import re
from typing import Any

from ..diagnostic import Diagnostics
from ..items import FieldItem
from ..types import MISSING, Missing, ParamTypeChk
from .input_section import InputSection


class DateTime(FieldItem):
    """A datetime input, converted to a Python datetime.

    Defaults accept strings or Python values and are emitted as ISO strings.
    Invalid declarations produce build diagnostics; invalid runtime values raise.
    Missing/None values use the default, then allow_none. No timezone is inferred.
    """

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [ParamTypeChk("default", (str, dt.datetime), MISSING)]
    )

    def __init__(
        self,
        *,
        name: str = "",
        description: str = "",
        default: str | dt.datetime | Missing = MISSING,
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
                self.default = parsed.isoformat(sep=" ")

    @staticmethod
    def _parse(value: str | dt.datetime) -> dt.datetime:
        if isinstance(value, str):
            if not re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T](?:[01][0-9]|2[0-3]):[0-9]{2}"
                r"(?::[0-9]{2}(?:\.[0-9]{1,6})?)?"
                r"(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9]"
                r"(?::[0-5][0-9](?:\.[0-9]{1,6})?)?)?",
                value,
            ):
                raise ValueError("DateTime requires a date and time")
            return dt.datetime.fromisoformat(value)
        if isinstance(value, dt.datetime):
            return value
        raise TypeError(f"Value of DateTime is not a datetime or string {value!r}")

    def convert(
        self, value: str | dt.datetime | None, diag: Diagnostics
    ) -> dt.datetime | None:
        value = self._resolve_none(value, diag)
        if value is None:
            return None
        try:
            return self._parse(value)
        except (TypeError, ValueError) as exc:
            diag.error(str(exc))
            raise

    def selector(self) -> dict[str, Any]:
        return {"datetime": {}}
