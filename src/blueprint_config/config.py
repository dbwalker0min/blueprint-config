from abc import ABC, abstractmethod
from typing import Any, ClassVar, Self

from .diagnostic import DiagnosticMessage, Diagnostics
from .items import FieldItem, InputSection
from .types import MISSING, ParamTypeChk


class BaseConfig(ABC):
    """Base class for all configuration objects."""

    VALID_FIELD_PROPERTIES: frozenset[ParamTypeChk] = frozenset()
    EXCLUDED_ITEMS: frozenset[str] = frozenset()

    # This registers all subclasses of ConfigObject in the _registry dictionary
    _registry: ClassVar[dict[tuple[str, str], Self]] = {}

    def __init_subclass__(cls, *, register: bool = True, **kwargs):
        super().__init_subclass__(**kwargs)
        print(f"initializing class {cls.__name__}")

        # keep the diagnostics for later access
        cls._build_diag = Diagnostics()

        # Register the most recent definition of this class
        if register:
            key = (cls.__module__, cls.__qualname__)
            BaseConfig._registry[key] = cls  # ty:ignore[invalid-assignment]

        # validate the fields and input sections
        for k, v in cls.blueprint_items().items():
            v.validate(cls, k, cls._build_diag)

        # validate myself
        cls.validate_config(cls._build_diag)

    def __init__(self, **values):
        # create the diagnostics if it doesn't already exist
        self._load_diag = getattr(self, '_load_diag', Diagnostics())

        # iterate over all field items and set their values
        for name, field in self.field_items().items():
            with self._load_diag.child(leaf=name):
                if name in values:
                    value = values.pop(name)

                elif (fld := getattr(field, "default", MISSING)) is not MISSING:
                    value = fld

                elif getattr(field, "allow_none", False):
                    value = None

                else:
                    self._load_diag.error(
                        "No value provided for field with no default value and 'allow_none' false"
                    )
                    return

                setattr(self, name, field.convert(value, self._load_diag))

    def get_load_diagnostics(self) -> list[DiagnosticMessage]:
        """Return the diagnostics for the configuration object after loading."""
        return self._load_diag.diagnostics

    @classmethod
    def get_build_diagnostics(cls) -> list[DiagnosticMessage]:
        """Return the diagnostics for the configuration object after building."""
        return cls._build_diag.diagnostics

    @classmethod
    def field_items(cls) -> dict[str, FieldItem]:
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
            if isinstance(value, (BaseConfig))
        }

    @classmethod
    def get_registry(cls) -> dict[tuple[str, str], type[BaseConfig]]:
        return BaseConfig._registry  # ty:ignore[invalid-return-type]

    def __repr__(self):
        """Return a string representation of the configuration object"""
        values = ", ".join(
            f"{name}={getattr(self, name)!r}" for name in self.field_items()
        )
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

    # Descriptor protocol methods for managing attribute access
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

    @classmethod
    @abstractmethod
    def render_field(cls, field: FieldItem) -> dict[str, Any]: ...

    @classmethod
    def validate_config(cls, diag: Diagnostics):
        return


class BlueprintConfig(BaseConfig, register=False):
    # Blueprint metadata and path of blueprint to write
    blueprint_name: str
    blueprint_path: str
    blueprint_description: str = ""
    blueprint_author: str = ""
    blueprint_minimum_version: str = ""

    @classmethod
    def render_field(cls, field: FieldItem) -> dict[str, Any]:
        """Render a blueprint fragment for the given field"""
        result = {}

        if v := getattr(field, "name", None):
            result["name"] = v

        if v := getattr(field, "description", None):
            result["description"] = v

        if (v := getattr(field, "default", MISSING)) is not MISSING:
            result["default"] = v

        result["selector"] = field.selector()
        return result


class EmbeddedObject(BaseConfig, register=False):
    EXCLUDED_ITEM_CLASSES = frozenset([InputSection])

    @classmethod
    def render_field(cls, field: FieldItem) -> dict[str, Any]:
        """Render a blueprint fragment for the given field as an object selector"""
        result = {}

        if v := getattr(field, "name", None):
            result["label"] = v

        if v := getattr(field, "required", None):
            result["required"] = v

        result["selector"] = field.selector()
        return result
