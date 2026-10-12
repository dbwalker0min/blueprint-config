from __future__ import annotations

from typing import Any, Literal

from ..diagnostic import Diagnostics
from ..items import FieldItem, InputSection
from ..types import MISSING, Missing, ParamTypeChk


class Number(FieldItem):
    """A numeric input with explicit Home Assistant selector options.

    Omitted selector options are left to Home Assistant's defaults. Runtime
    integers and floats become floats; bool and numeric strings are rejected.
    Declaration errors are collected during configuration-class construction.
    Home Assistant supports translation_key in integration contexts, but it has
    no effect in the blueprint editor, so this API intentionally omits it.
    """

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [
            ParamTypeChk("default", (int, float), MISSING),
            ParamTypeChk("min", (int, float), MISSING),
            ParamTypeChk("max", (int, float), MISSING),
            ParamTypeChk(
                "step",
                (int, float, str),
                MISSING,
                validator=lambda value: (
                    value == "any" or (type(value) in (int, float) and value > 0)
                ),
            ),
            ParamTypeChk("unit_of_measurement", str, MISSING),
            ParamTypeChk("mode", str, MISSING, validator=("box", "slider")),
        ]
    )

    def __init__(
        self,
        *,
        name: str = "",
        description: str = "",
        default: float | Missing = MISSING,
        allow_none: bool = False,
        section: InputSection | None = None,
        min: float | Missing = MISSING,
        max: float | Missing = MISSING,
        step: float | Literal["any"] | Missing = MISSING,
        unit_of_measurement: str | Missing = MISSING,
        mode: Literal["box", "slider"] | Missing = MISSING,
    ) -> None:
        super().__init__(
            name=name,
            description=description,
            default=default,
            allow_none=allow_none,
            min=min,
            max=max,
            step=step,
            unit_of_measurement=unit_of_measurement,
            mode=mode,
            **({"section": section} if section is not None else {}),
        )

    def convert(self, value: float | None, diag: Diagnostics) -> float | None:
        value = self._resolve_none(value, diag)
        if value is None:
            return None
        if type(value) not in (int, float):
            raise TypeError(f"Value of Number is not numeric or None {value!r}")
        return float(value)

    def selector(self) -> dict[str, Any]:
        number = {}
        for parameter in (
            "min",
            "max",
            "step",
            "unit_of_measurement",
            "mode",
        ):
            value = getattr(self, parameter, MISSING)
            if value is not MISSING:
                number[parameter] = value
        return {"number": number}
