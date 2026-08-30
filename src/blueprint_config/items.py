from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from copy import copy
from typing import TYPE_CHECKING, Any

from .diagnostic import Diagnostics
from .types import MISSING, ParamTypeChk, Status

if TYPE_CHECKING:
    from .config import BaseConfig


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
        # This is a local copy of the arguments. Used during argument consumption.
        self._field_args = {}
        # This is a list of valid fields. Populated during argument consumption.
        self._valid_fields = set()
        # These are the diagnostics for validation. Created during the validate method.
        self._validate_diagnostics: Diagnostics | None = None
        # Field name for this blueprint item. Set in validate.
        self._field_name: str = ""


        # The parent class that this blueprint item belongs to. Set in validate.
        self._parent_class: type[BaseConfig] | None = None

        # Set these values to their defaults. They will be updated during argument consumption.
        self.name: str | None = None
        self.description: str | None = None
        self.allow_none: bool = False
        self.multiple: bool = False
        self.label_field: str | None = None
        self.description_field: str | None = None
        self.collapsed: bool = False
        self.section = None

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

        # Set the value of the attribute and mark it as a valid field
        setattr(self, param_chk.param, value)
        self._valid_fields.add(param_chk.param)

    def is_valid_field(self, field_name: str) -> bool:
        """Check if a field name is valid for this blueprint item."""
        return field_name in self._valid_fields

    def validate(
        self,
        parent: type[BaseConfig],
        field_name: str,
        diag: Diagnostics | None,
    ):
        """Validate the blueprint using the diagnostics object.

        Args:
            parent (type[BaseConfig]): The parent configuration class.
            field_name (str): The name of the field being validated.
            diag (Diagnostics | None): The diagnostics object to record validation messages.
        """
        if diag is None:
            raise ValueError("Diagnostics object must be provided for validation")

        self._field_args = copy(self._original_field_arguments)

        # don't pass around the diagnostics object to the field name
        self._validate_diagnostics = diag
        self._field_name = field_name
        self._parent_class: type[BaseConfig] | None = parent

        # Make certain the parent class is a subclass of BaseConfig
        assert parent is not None, "Parent must be a subclass of BaseConfig"

        # Get (most) of the type checking parameters for the field
        type_checking: frozenset[ParamTypeChk] = (
            self.__class__.FIELD_PARAM_TYPE_CHECKS
            | frozenset(
                [
                    ParamTypeChk("name", str, ""),
                    ParamTypeChk("description", str, ""),
                    ParamTypeChk("allow_none", bool, False),
                ]
            )
        )
        for parameter_chk in type_checking:
            self._consume_arg(parameter_chk)

        # Check for any remaining unused field arguments
        # Give a warning because the parameter will be ignored
        for parameter_name, value in self._field_args.items():
            self._validate_diagnostics.warning(
                f"From field {self._field_name}: "
                f"Unused field argument: {parameter_name}={value}"
            )
        self._validate_diagnostics = None

    @abstractmethod
    def selector(self) -> dict[str, Any]:
        """Return a dictionary that uniquely identifies this blueprint item."""


class InputSection(BlueprintItem):
    """This provides a new section in the blueprint"""

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [
            ParamTypeChk("icon", str, ""),
            ParamTypeChk("collapsed", bool, False),
        ]
    )

    def selector(self) -> dict[str, Any]:
        assert self._parent_class is not None, "Parent class must not be None"

        result = {}
        if self.name is not None:
            result["name"] = self.name

        if self.description is not None:
            result["description"] = self.description

        # if not emitted, this field defaults to false
        if self.collapsed:
            result["collapsed"] = True

        inputs = {}

        # Find all the fields that reference this object
        for f, v in self._parent_class.field_items().items():
            if v.section is self:
                inputs[f] = self._parent_class.render_field(v)

        result["inputs"] = inputs
        return result


class FieldItem(BlueprintItem, ABC):
    """This is a base class for items that are fields within a blueprint. Fields store data."""

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        BlueprintItem.FIELD_PARAM_TYPE_CHECKS
        | frozenset(
            [
                ParamTypeChk("section", InputSection, None),
            ]
        )
    )

    @abstractmethod
    def convert(self, value: Any, diag: Diagnostics) -> Status: ...
