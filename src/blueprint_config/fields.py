from __future__ import annotations

import datetime as dt
import inspect
from abc import ABC, abstractmethod
from collections.abc import Collection
from typing import Any, ClassVar, Self

from .diagnostic import DiagnosticMessage, Diagnostics
from .types import MISSING, _Missing, Status


class FieldItem(ABC):
    """This is a base class for items that can be part of a blueprint or embedded object.
    It represents the common attribues for the blueprint schema"""

    def __init__(
        self,
        *,
        name: _Missing = MISSING,
        default: Any = MISSING,
        required: bool | _Missing = MISSING,
        description: str | _Missing = MISSING,
        section: InputSection | _Missing = MISSING,
        allow_none: bool | _Missing = MISSING,
        **kwargs,
    ):
        # Do this first before anyone adds more variables
        # This keeps track of *all* variables that have been explicitly specified
        specified_values: set[str] = {
            f
            for f, v in locals().items()
            if f not in {"self", "__class__", "kwargs"} and v is not MISSING
        } | set(kwargs)

        super().__init__()
        self.specified_values = specified_values

        # Keep track of unknown parameters
        self.unknown_parameters: set[str] = set(kwargs)

        self.name = (
            "" if name is MISSING else name.strip() if isinstance(name, str) else name
        )

        self.description = (
            ""
            if description is MISSING
            else inspect.cleandoc(description)
            if isinstance(description, str)
            else description
        )

        self.required = False if required is MISSING else required
        self.section = None if section is MISSING else section
        self.allow_none = False if allow_none is MISSING else allow_none

        # allow missing to propagate
        self.default = default

    @abstractmethod
    def validate(
        self, field_name: str, diag: Diagnostics, valid_properties: Collection[str]
    ): ...

    @abstractmethod
    def convert(self, value: Any) -> Any: ...

    @abstractmethod
    def selector(self) -> dict[str, Any]: ...


class ConfigObject(ABC):
    _registry: ClassVar[dict[tuple[str, str], Self]] = {}
    VALID_FIELD_PROPERTIES: frozenset[str] = frozenset()

    def __init_subclass__(cls, *, register: bool = True, **kwargs):
        super().__init_subclass__(**kwargs)
        print(f"initializing class {cls.__name__}")

        # keep the diagnostics for later access
        cls._diag = Diagnostics()

        # Register the most recent definition of this class
        if register:
            key = (cls.__module__, cls.__qualname__)
            ConfigObject._registry[key] = cls  # ty:ignore[invalid-assignment]

        # validate the fields and input sections
        for k, v in cls.blueprint_items().items():
            v.validate(k, cls._diag, cls.VALID_FIELD_PROPERTIES)

        # validate myself
        cls.validate(cls._diag)

    def __init__(self, *, _diag: Diagnostics | None = None, **values):
        self._load_diag = _diag or Diagnostics()

        for name, field in self.fields().items():
            if name in values:
                value = values.pop(name)

            elif field.default is not MISSING:
                value = field.default

            elif field.allow_none:
                value = None

            else:
                self._load_diag.error(
                    "No value provided for field with no default value and 'allow_none' false",
                    use_path=True,
                )
                return

            setattr(self, name, field.convert(value))

    def get_load_diagnostics(self) -> list[DiagnosticMessage]:
        return self._load_diag.diagnostics

    @classmethod
    def diagnostics(cls) -> Diagnostics:
        return cls._diag

    @classmethod
    def fields(cls) -> dict[str, FieldItem]:
        """Return items that are fields in the configuration object"""
        return {
            name: value
            for name, value in cls.__dict__.items()
            if isinstance(value, FieldItem)
        }

    @classmethod
    def blueprint_items(cls) -> dict[str, FieldItem]:
        """Return items that are blueprint items (Fields or Sections)"""
        return {
            name: value
            for name, value in cls.__dict__.items()
            if isinstance(value, FieldItem)
        }

    @classmethod
    def get_registry(cls) -> dict[tuple[str, str], type[ConfigObject]]:
        return ConfigObject._registry  # ty:ignore[invalid-return-type]

    def __repr__(self):
        """Return a string representation of the configuration object"""
        values = ", ".join(f"{name}={getattr(self, name)!r}" for name in self.fields())
        return f"{type(self).__name__}({values})"

    @classmethod
    def from_dict(cls, values):
        """Create an instance of the configuration object from a dictionary of values."""
        return cls(**values)

    @classmethod
    def blueprint_fragment(cls) -> dict[str, Any]:
        """Generate a blueprint fragment for the object"""
        result = {}

        for name, item in cls.blueprint_items().items():
            result[name] = cls.render_field(item)

        return result

    @classmethod
    @abstractmethod
    def render_field(cls, field: FieldItem) -> dict[str, Any]: ...

    @classmethod
    def validate(cls, diagnostics: Diagnostics):
        """Validate the configuration object and post any diagnostics to the provided diagnostics object"""
        if len(cls.fields()) == 0:
            cls._diag.error(
                f"No fields defined in the configuration object {cls.__name__!r}."
            )


class BlueprintObject(ConfigObject, register=False):
    VALID_FIELD_PROPERTIES: frozenset[str] = frozenset(
        ["name", "description", "default", "allow_none", "section"]
    )

    # Name and path of the blueprint to write
    blueprint_name: str
    blueprint_path: str

    @classmethod
    def validate(cls, diagnostics: Diagnostics):
        """Validate the configuration object and post any diagnostics to the provided diagnostics object"""
        super().validate(diagnostics)

    @classmethod
    def render_field(cls, field: FieldItem) -> dict[str, Any]:
        """Render a blueprint fragment for the given field"""
        result = {}

        if field.name:
            result["name"] = field.name

        if field.description:
            result["description"] = field.description

        if field.default is not MISSING:
            result["default"] = field.default

        result["selector"] = field.selector()
        return result


class Field(FieldItem, ABC):
    """This is a base class for fields in a configuration object. It provides common functionality for all fields."""

    def validate(
        self, field_name: str, diag: Diagnostics, valid_properties: Collection[str]
    ):
        """Validate the provided arguments to the field"""
        for parameter_name, expected_type, allow_missing in GENERIC_FIELD_VALIDATION:
            # just check the values that were specified
            if parameter_name not in self.specified_values:
                continue
            # The parameter was specified, so we need to validate it
            if parameter_name in valid_properties:
                value: Any = getattr(self, parameter_name)
                diag.type_check_error(
                    field_name, parameter_name, expected_type, value, allow_missing
                )
            else:
                diag.error(
                    f"Property {parameter_name!r} is not allowed here", field_name
                )

        # report any unknown parameters
        for parameter_name in self.unknown_parameters:
            diag.error(f"Unknown parameter {parameter_name!r}", field_name)

    def __set_name__(self, owner, name: str):
        """This is called when the field is assigned to a class attribute"""
        self.attr_name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        return instance.__dict__[self.attr_name]

    def __set__(self, instance, value):
        if instance is None:
            return self

        instance.__dict__[self.attr_name] = value

    @abstractmethod
    def convert(self, value): ...

    @abstractmethod
    def selector(self) -> dict: ...


class Boolean(Field):
    def __init__(self, default: bool | None | _Missing = MISSING, **kwargs):
        super().__init__(default=default, **kwargs)

    def convert(self, value: bool | None):
        if isinstance(value, bool):
            return value

        if value is None:
            if self.default is not MISSING:
                return self.default

            if self.allow_none:
                return None

            raise ValueError("Boolean field has no default and no value was provided")
        raise TypeError(f"Value of Boolean is not boolean or None {value!r}")

    def selector(self) -> dict:
        return {"boolean": {}}

    def validate(
        self, field_name: str, diag: Diagnostics, valid_properties: Collection[str]
    ):
        super().validate(field_name, diag, valid_properties)

        # just check the type of the default value.
        diag.type_check_error(field_name, "default", bool, self.default, True)


class Time(Field):
    def convert(self, value):
        if isinstance(value, str):
            return dt.time.fromisoformat(value)

        return value

    def selector(self) -> dict:
        return {"time": {}}

    def validate(
        self, field_name: str, diag: Diagnostics, valid_properties: Collection[str]
    ):
        super().validate(field_name, diag, valid_properties)

        # check the default type
        d = self.default
        if d is not MISSING and d is not None:
            diag.type_check_error(field_name, "default", dt.time, d)


class Object(Field):
    def __init__(
        self,
        object_type: type[ConfigObject] | _Missing = MISSING,
        *,
        multiple: bool | _Missing = MISSING,
        label_field: str | _Missing = MISSING,
        description_field: str | _Missing = MISSING,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.object_type = object_type
        self.multiple = False if multiple is MISSING else multiple
        self.label_field = label_field
        self.description_field = description_field

    def validate(
        self, field_name: str, diag: Diagnostics, valid_properties: Collection[str]
    ):
        super().validate(field_name, diag, valid_properties)

        # Check multiple is a boolean
        diag.type_check_error(field_name, "multiple", bool, self.multiple)

        # Check `object_type` is a class derived from `ConfigObject`
        ot = self.object_type
        if ot is MISSING:
            diag.error(
                "'object_type' must be a class derived from 'ConfigObject'. Is missing",
                field_name,
            )
            return
        if isinstance(ot, type):
            if not issubclass(ot, ConfigObject):
                class_heir: list[str] = [
                    f"'{cls.__name__}'" for cls in ot.__mro__[1:] if cls is not object
                ]
                if len(class_heir) == 0:
                    class_heir = ["nothing"]
                heir_str = "->".join(class_heir)
                m = (
                    "'object_type' must be a class derived from 'ConfigObject'. "
                    f"Class {type(ot).__name__!r} is derived from {heir_str}"
                )
                diag.error(m, field_name)
                return

            # check that the label and description fields are valid field names
            field_names = ot.fields()
            for p in ["label_field", "description_field"]:
                value = getattr(self, p)
                if value is MISSING:
                    continue
                if (
                    diag.type_check_error(
                        field_name, p, str, value, allow_missing=False
                    ) == Status.VALID
                    and value not in field_names
                ):
                    m = (
                        f"parameter {p!r} ({value!r}) does not reference "
                        f"a valid field in {ot.__name__!r}."
                    )
                    diag.error(m, field_name)
            return

        diag.error(
            f"'object_type' must be a class derived from 'ConfigObject'. "
            f"Is of type {type(ot).__name__!r}",
            field_name,
        )

    def convert(self, value):
        if value is None:
            return [] if self.multiple else None

        if self.multiple:
            return [self.object_type.from_dict(item) for item in value]

        return self.object_type.from_dict(value)

    def selector(self) -> dict:
        return
        obj = {
            "fields": self.object_type.blueprint_fragment(
                BlueprintContext.OBJECT_FIELDS
            )
        }

        if self.multiple:
            obj["multiple"] = True

        if self.label_field is not MISSING:
            obj["label_field"] = self.label_field

        if self.description_field is not MISSING:
            obj["description_field"] = self.description_field

        return {"object": obj}


class InputSection:
    """This provides a new section in the blueprint"""

    def __init__(
        self,
        *,
        name=None,
        description=None,
        icon=None,
        collapsed=False,
    ):
        self.name = name
        self.description = description
        self.icon = icon
        self.collapsed = collapsed
        self.attr_name = None
        self._diag = Diagnostics()

    def validate(
        self,
        field_name: str,
        diag: Diagnostics,
        valid_properties: frozenset[str] = frozenset(),
    ):
        pass

    def __set_name__(self, owner, name):
        self.attr_name = name

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


# This is for validating the generic field
# Fields are parameter name, expected type, and whether None is allowed
GENERIC_FIELD_VALIDATION = [
    ("name", str, False),
    ("required", bool, False),
    ("description", str, False),
    ("section", InputSection, True),
    ("allow_none", bool, False),
]
