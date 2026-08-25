from __future__ import annotations

import datetime as dt
import inspect
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, ClassVar, Self

from .diagnostic import Diagnostics
from .types import MISSING, _Missing


class BlueprintContext(Enum):
    INPUT = auto()
    OBJECT_FIELDS = auto()


class ConfigObject:
    _registry: ClassVar[dict[tuple[str, str], Self]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        # keep the diagnostics for later access
        cls._diag = Diagnostics()

        # Register the most recent definition of this class
        key = (cls.__module__, cls.__qualname__)
        ConfigObject._registry[key] = cls  # ty:ignore[invalid-assignment]

        # validate the fields and input sections
        for k, v in cls.blueprint_items().items():
            v.validate(k, cls._diag)

    @classmethod
    def fields(cls) -> dict[str, Field]:
        return {
            name: value
            for name, value in cls.__dict__.items()
            if isinstance(value, Field)
        }

    @classmethod
    def blueprint_items(cls) -> dict[str, Field | InputSection]:
        """Return items that are blueprint items (Fields or Sections)"""
        return {
            name: value
            for name, value in cls.__dict__.items()
            if isinstance(value, (Field, InputSection))
        }

    def __init__(self, **values):
        for name, field in self.fields().items():
            if name in values:
                value = values.pop(name)

            elif field.default is not MISSING:
                value = field.default

            elif field.required:
                raise ValueError(f"Missing required field: {name}")

            else:
                value = None

            setattr(self, name, field.convert(value))

        if values:
            raise ValueError(f"Unknown fields: {', '.join(values)}")

    @classmethod
    def from_dict(cls, values):
        return cls(**values)

    def __repr__(self):
        values = ", ".join(f"{name}={getattr(self, name)!r}" for name in self.fields())
        return f"{type(self).__name__}({values})"

    @classmethod
    def blueprint_fragment(cls, context: BlueprintContext) -> dict:
        """Generate a blueprint fragment for the object"""
        result = {}

        for name, item in cls.blueprint_items().items():
            if isinstance(item, InputSection):
                # This is an input section
                result[name] = item.blueprint_fragment(
                    {k: v for k, v in cls.fields().items() if v.section is item}
                )

            elif item.section is None:
                result[name] = item.blueprint_fragment(context)

            # A field belonging to a section was already emitted
            # when its InputSection was encountered.

        return result


class BlueprintItem(ABC):
    """This is a base class for items that can be part of a blueprint"""

    @abstractmethod
    def validate(self, field_name: str, diag: Diagnostics):
        """Verify the blueprint item and post any diagnostics to diag"""

    @abstractmethod
    def blueprint_fragment(self, context: BlueprintContext) -> dict[str, Any]:
        """Generate a blueprint fragment for the item"""


class Field(BlueprintItem, ABC):
    """This is a base class for fields in a configuration object. It provides common functionality for all fields."""

    def __init__(
        self,
        *,
        name: str = "",
        default: Any = MISSING,
        required: bool = False,
        description: str = "",
        section: InputSection | _Missing = MISSING,
        allow_none: bool = False,
    ):
        super().__init__()
        self.name = name = name.strip() if isinstance(name, str) else name
        self.default = default
        self.required = required
        self.description = (
            inspect.cleandoc(description)
            if isinstance(description, str)
            else description
        )
        self.section = section
        self.allow_none = allow_none

    def validate(self, field_name: str, diag: Diagnostics):
        """Validate the provided arguments to the field"""
        for p, t, a_none in GENERIC_FIELD_VALIDATION:
            value = getattr(self, p)
            diag.type_check_error(field_name, p, t, value, a_none)

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

    def blueprint_fragment(self, context: BlueprintContext) -> dict[str, Any]:
        result = {}

        if context == BlueprintContext.INPUT:
            if self.name:
                result["name"] = self.name

            if self.description:
                result["description"] = self.description

            if self.default is not MISSING:
                result["default"] = self.default
        elif context == BlueprintContext.OBJECT_FIELDS:
            # Context is for Objects
            if self.name:
                result["label"] = self.name

            if self.required and self.required:
                result["required"] = True
        else:
            raise ValueError(f"Unknown context: {context}")

        # get the selector from the given subclass
        result["selector"] = self.selector()

        return result


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

    def validate(self, field_name: str, diag: Diagnostics):
        super().validate(field_name, diag)

        # just check the type of the default value.
        diag.type_check_error(field_name, "default", bool, self.default, True)


class Time(Field):
    def convert(self, value):
        if isinstance(value, str):
            return dt.time.fromisoformat(value)

        return value

    def selector(self) -> dict:
        return {"time": {}}

    def validate(self, field_name: str, diag: Diagnostics):
        super().validate(field_name, diag)

        # check the default type
        d = self.default
        if d is not MISSING and d is not None:
            diag.type_check_error(field_name, "default", dt.time, d)


class Object(Field):
    def __init__(
        self,
        object_type: type[ConfigObject] | _Missing = MISSING,
        *,
        multiple: bool = False,
        label_field: str | _Missing = MISSING,
        description_field: str | _Missing = MISSING,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.object_type = object_type
        self.multiple = multiple
        self.label_field = label_field
        self.description_field = description_field

    def validate(self, field_name: str, diag: Diagnostics):
        super().validate(field_name, diag)

        # Check multiple is a boolean
        diag.type_check_error(field_name, "multiple", bool, self.multiple)

        # Check `object_type` is a class derived from `ConfigObject`
        ot = self.object_type
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
                if (
                    diag.type_check_error(field_name, p, str, value, allow_missing=True)
                    and value is not MISSING
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

    def validate(self, field_name: str, diag: Diagnostics):
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
