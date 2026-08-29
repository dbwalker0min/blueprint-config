from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import copy
from typing import TYPE_CHECKING, Any

from .diagnostic import Diagnostics
from .types import MISSING, ParamTypeChk, Status

if TYPE_CHECKING:
    from .fields import ConfigObject


class BlueprintItem(ABC):
    """This is a base class for items that have a blueprint representation."""

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [
            ParamTypeChk("name", str, ""),
            ParamTypeChk("description", str, ""),
            ParamTypeChk("allow_none", bool, False),
        ]
    )

    def __init__(
        self,
        **field_arguments,
    ):
        self._original_field_arguments = field_arguments
        self._field_args = {}
        self._validate_diagnostics: Diagnostics | None = None

    def _consume_arg(
        self,
        param_chk: ParamTypeChk,
        convert: Callable[[Any], Any] | None = None,
    ):
        """Consume a field argument, performing type checking and conversion if necessary.

        Args:
            parameter_chk (ParamTypeChk): The parameter type check information.
            convert (Callable[[Any], Any] | None): Optional conversion function to apply to the value.
        """
        if self._validate_diagnostics is None:
            raise RuntimeError(
                "Validation diagnostics not set before consuming arguments"
            )

        value = self._field_args.pop(param_chk.param, MISSING)

        value_type = type(value)
        if value is MISSING:
            value = param_chk.default
        elif param_chk.exp_type is not value_type:
            msg = (
                f"From field {self._field_name}: "
                f"Expected type {param_chk.exp_type.__name__!r}, "
                f"got type {value_type.__name__!r}"
            )
            self._validate_diagnostics.error(msg)
            value = param_chk.default
        elif convert is not None:
            value = convert(value)

        setattr(self, param_chk.param, value)

    def validate(
        self,
        cls: type[ConfigObject],
        field_name: str,
        diag: Diagnostics,
    ):
        if diag is None:
            raise ValueError("Diagnostics object must be provided for validation")

        self._field_args = copy(self._original_field_arguments)

        # don't pass around the diagnostics object to the field name
        self._validate_diagnostics = diag
        self._field_name = field_name

        type_checking: frozenset[ParamTypeChk] = cls.VALID_FIELD_PROPERTIES | frozenset(
            [
                ParamTypeChk("name", str, ""),
                ParamTypeChk("description", str, ""),
                ParamTypeChk("allow_none", bool, False),
            ]
        )
        for parameter_chk in type_checking:
            self._consume_arg(parameter_chk)

        # Check for any remaining unused field arguments
        for parameter_name, value in self._field_args.items():
            self._validate_diagnostics.warning(
                f"From field {self._field_name}: "
                f"Unused field argument: {parameter_name}={value}"
            )
        self._validate_diagnostics = None

    @abstractmethod
    def selector(self) -> dict[str, Any]: ...


class FieldItem(BlueprintItem, ABC):
    """This is a base class for items that are fields within a blueprint. Fields store data."""

    @abstractmethod
    def convert(self, value: Any, diag: Diagnostics) -> Status: ...


class InputSection(BlueprintItem):
    """This provides a new section in the blueprint"""
    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset([
        ParamTypeChk("icon", str, ""),
        ParamTypeChk("collapsed", bool, False),
    ])

    def validate(self, cls, field_name: str, diag: Diagnostics):
        super().validate(cls, field_name, diag)

    def selector(self) -> dict[str, Any]:
        result = {}
        name = getattr(self, "name", None)
        if name is not None:
            result["name"] = name

        description = getattr(self, "description", None)
        if description is not None:
            result["description"] = description

        # if not emitted, this field defaults to false
        collapsed = getattr(self, "collapsed", False)
        if collapsed:
            result["collapsed"] = True

        # Find all the fields that reference this object
        for f in self.field_items():
            if getattr(f, "references", None) is self._field_name:
        return result

    def blueprint_fragment(self, inputs: dict[str, Any]):
        result = {
            "name": self.name,
            "input": {k: v.blueprint_fragment() for k, v in inputs.items()},
        }
        if self.description is not None:
            result["description"] = self.description

        if self.icon is not None:
            result["icon"] = self.icon

        if self.collapsed:
            result["collapsed"] = True

        return result
