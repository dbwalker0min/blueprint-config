from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from .config import BlueprintConfig
from .diagnostic import Diagnostics
from .items import FieldItem, InputSection
from .types import MISSING, Missing, ParamTypeChk


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


class Time(FieldItem):
    def convert(self, value: str | dt.time, diag: Diagnostics | None = None):
        if isinstance(value, str):
            return dt.time.fromisoformat(value)

        return value

    def selector(self) -> dict:
        return {"time": {}}


class Object(FieldItem):
    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [
            ParamTypeChk("multiple", bool, False),
            ParamTypeChk("label_field", str, ""),
            ParamTypeChk("description_field", str, ""),
        ]
    )

    def convert(self, value: Any, diag: Diagnostics):
        # This would occur if there were an error during parsing
        if self._parent_class is None or (
            self._parent_class is not None
            and not issubclass(self._parent_class, BlueprintConfig)
        ):
            raise TypeError(
                f"'object_class' must be a class derived from 'BlueprintConfig'. "
                f"Is of type {type(self._parent_class).__name__!r}"
            )

        multiple = getattr(self, "multiple", False)
        allow_none = getattr(self, "allow_none", False)
        if value is None and allow_none:
            return [] if multiple else None

        if multiple:
            return [self._parent_class.from_dict(item) for item in value]

        return self._parent_class.from_dict(value)

    def selector(self) -> dict:
        # check the type on parent class. If it is None or it not a subclass of BlueprintConfig, return an empty dict
        if self._parent_class is None or not issubclass(
            self._parent_class, BlueprintConfig
        ):
            return {}

        obj: dict[str, Any] = {"fields": self._parent_class.blueprint_fragment()}

        if getattr(self, "multiple", False):
            obj["multiple"] = True

        if v := getattr(self, "label_field", MISSING) is not MISSING:
            obj["label_field"] = v

        if v := getattr(self, "description_field", MISSING) is not MISSING:
            obj["description_field"] = v

        return {"object": obj}


class Number(FieldItem):
    """A numeric input with explicit Home Assistant selector options.

    Omitted selector options are left to Home Assistant's defaults. Runtime
    integers and floats become floats; bool and numeric strings are rejected.
    Declaration errors are collected during configuration-class construction.
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
            ParamTypeChk("translation_key", str, MISSING),
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
        translation_key: str | Missing = MISSING,
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
            translation_key=translation_key,
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
            "translation_key",
        ):
            value = getattr(self, parameter, MISSING)
            if value is not MISSING:
                number[parameter] = value
        return {"number": number}
