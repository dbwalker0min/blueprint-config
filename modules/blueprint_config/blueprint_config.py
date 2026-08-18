import datetime as dt
import types
from abc import ABC
from collections.abc import Callable, Mapping
from typing import (
    Any,
    ClassVar,
    Self,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

import attrs
from homeassistant.components.script import (
    blueprint_in_script,
    scripts_with_blueprint,
)
from homeassistant.components.script.const import DOMAIN as SCRIPT_DOMAIN
from homeassistant.const import EVENT_SERVICE_REGISTERED
from homeassistant.helpers import entity_registry as er
from stubs.pyscript_builtins import hass, pyscript_compile, service


T = TypeVar("T")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BlueprintConfigError(RuntimeError):
    """Base exception for blueprint configuration errors."""


class BlueprintConfigCardinalityError(BlueprintConfigError):
    """Raised when the number of configuration scripts is invalid."""


# ---------------------------------------------------------------------------
# Representation converters / validators
# ---------------------------------------------------------------------------


@pyscript_compile
def to_time(
    value: str | dt.time | None,
) -> dt.time | None:
    """Convert a Home Assistant time value to datetime.time."""
    if value is None or isinstance(value, dt.time):
        return value

    return dt.time.fromisoformat(value)


@pyscript_compile
def to_timedelta(
    value: Mapping[str, int | float] | dt.timedelta | None,
) -> dt.timedelta | None:
    """Convert a Home Assistant duration value to datetime.timedelta."""
    if value is None or isinstance(value, dt.timedelta):
        return value

    return dt.timedelta(**dict(value))


@pyscript_compile
def not_none(instance: Any, attribute: Any, value: Any) -> None:
    """attrs validator for fields that must not be None."""
    if value is None:
        raise ValueError(f"{attribute.name} is required")


# ---------------------------------------------------------------------------
# Configuration object construction
# ---------------------------------------------------------------------------


class ConfigObject:
    """Base class for structured blueprint configuration objects."""

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any],
    ) -> Self:
        """Construct this attrs object recursively from a mapping."""
        if not isinstance(data, Mapping):
            raise TypeError(
                f"{cls.__name__} requires a mapping; "
                f"got {type(data).__name__}"
            )

        if not attrs.has(cls):
            raise TypeError(
                f"{cls.__name__} must be an attrs class"
            )

        attributes = attrs.fields(cls)
        field_names = {attribute.name for attribute in attributes}

        unknown = set(data) - field_names
        if unknown:
            names = ", ".join(sorted(str(name) for name in unknown))
            raise TypeError(
                f"Unknown field(s) for {cls.__name__}: {names}"
            )

        # get_type_hints() also handles generated modules that use postponed
        # annotations.  The attrs Attribute.type value alone might be a string.
        type_hints = get_type_hints(cls)

        values: dict[str, Any] = {}

        for attribute in attributes:
            # Do not manufacture None for an absent field.  Leaving it out
            # allows the attrs class's own default/default_factory to apply.
            if attribute.name not in data:
                continue

            annotation = type_hints.get(
                attribute.name,
                attribute.type,
            )

            values[attribute.name] = _convert_structure(
                annotation,
                data[attribute.name],
                path=f"{cls.__name__}.{attribute.name}",
            )

        return cls(**values)


def _convert_structure(
    annotation: Any,
    value: Any,
    *,
    path: str,
) -> Any:
    """Recursively convert structural configuration values."""
    if value is None:
        return None

    origin = get_origin(annotation)

    # T | None or Optional[T]
    if origin in (Union, types.UnionType):
        args = tuple(
            arg
            for arg in get_args(annotation)
            if arg is not type(None)
        )

        if len(args) == 1:
            return _convert_structure(
                args[0],
                value,
                path=path,
            )

        # There is no generated use case for arbitrary unions yet.
        # Leave those to the attrs constructor/application.
        return value

    # A directly nested configuration object.
    if (
        isinstance(annotation, type)
        and issubclass(annotation, ConfigObject)
    ):
        if not isinstance(value, Mapping):
            raise TypeError(
                f"{path} requires a mapping; "
                f"got {type(value).__name__}"
            )

        return annotation.from_mapping(value)

    # Multiple selector / repeated object.
    if origin is tuple:
        if not isinstance(value, (list, tuple)):
            raise TypeError(
                f"{path} requires a list or tuple; "
                f"got {type(value).__name__}"
            )

        args = get_args(annotation)

        # tuple[T, ...]
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(
                _convert_structure(
                    args[0],
                    item,
                    path=f"{path}[{index}]",
                )
                for index, item in enumerate(value)
            )

        # Bare tuple
        if not args:
            return tuple(value)

        # Fixed-length tuple, should we ever generate one.
        if len(args) != len(value):
            raise TypeError(
                f"{path} requires {len(args)} elements; "
                f"got {len(value)}"
            )

        return tuple(
            _convert_structure(
                item_type,
                item,
                path=f"{path}[{index}]",
            )
            for index, (item_type, item) in enumerate(
                zip(args, value, strict=True)
            )
        )

    # Scalars are passed through.  attrs converters such as to_time() and
    # to_timedelta() perform representation conversion during construction.
    return value


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


Defaults = dict[type[ConfigObject], dict[str, Any]]


def apply_defaults(
    inp: T,
    defaults: Defaults,
) -> T:
    """Recursively apply type-specific defaults to None attrs fields."""

    if isinstance(inp, tuple):
        new_values = tuple(
            apply_defaults(value, defaults)
            for value in inp
        )

        # Preserve identity if recursion made no changes.
        if all(
            old is new
            for old, new in zip(inp, new_values, strict=True)
        ):
            return inp

        return cast(T, new_values)

    if not attrs.has(type(inp)):
        return inp

    changes: dict[str, Any] = {}

    # First recurse through this object's fields.
    for attribute in attrs.fields(type(inp)):
        value = getattr(inp, attribute.name)
        new_value = apply_defaults(value, defaults)

        if new_value is not value:
            changes[attribute.name] = new_value

    # Then apply defaults belonging specifically to this attrs type.
    object_defaults = defaults.get(type(inp), {})

    for name, default in object_defaults.items():
        value = changes.get(name, getattr(inp, name))

        if value is None and default is not None:
            changes[name] = default

    if not changes:
        return inp

    return cast(T, attrs.evolve(inp, **changes))


# ---------------------------------------------------------------------------
# Home Assistant script lookup / retrieval
# ---------------------------------------------------------------------------


def _script_entity_for_blueprint(
    blueprint_path: str,
) -> str:
    """Return the one script entity using a blueprint."""
    entity_ids = scripts_with_blueprint(
        hass,
        blueprint_path,
    )

    n_entities = len(entity_ids)

    if n_entities != 1:
        raise BlueprintConfigCardinalityError(
            f"Blueprint {blueprint_path!r} requires exactly one "
            f"configuration script; found {n_entities}"
        )

    return entity_ids[0]


def _script_service_for_entity(
    entity_id: str,
) -> str:
    """Return the immutable script service name for an entity."""
    registry_entry = er.async_get(hass).async_get(entity_id)

    if registry_entry is None:
        raise BlueprintConfigError(
            f"No entity registry entry for {entity_id}"
        )

    if not registry_entry.unique_id:
        raise BlueprintConfigError(
            f"Script {entity_id} has no unique_id"
        )

    return registry_entry.unique_id


def _script_service_for_blueprint(
    blueprint_path: str,
) -> str:
    """Return the one script service associated with a blueprint."""
    return _script_service_for_entity(
        _script_entity_for_blueprint(blueprint_path)
    )


def load_one(
    blueprint_path: str,
) -> Mapping[str, Any]:
    """Load the raw response from exactly one blueprint configuration."""
    entity_id = _script_entity_for_blueprint(
        blueprint_path
    )

    script_service = _script_service_for_entity(
        entity_id
    )

    response = service.call(
        SCRIPT_DOMAIN,
        script_service,
        return_response=True,
    )

    if not isinstance(response, Mapping):
        raise BlueprintConfigError(
            f"{entity_id} returned "
            f"{type(response).__name__}; expected a mapping"
        )

    return response


def blueprint_from_script_service(
    service_name: str,
) -> str | None:
    """Return the blueprint path associated with a script service."""
    registry = er.async_get(hass)

    entity_id = registry.async_get_entity_id(
        SCRIPT_DOMAIN,
        SCRIPT_DOMAIN,
        service_name,
    )

    if entity_id is None:
        return None

    return blueprint_in_script(
        hass,
        entity_id,
    )


# ---------------------------------------------------------------------------
# Root blueprint-backed configuration
# ---------------------------------------------------------------------------


class BlueprintConfig(ConfigObject, ABC):
    """Base class for a blueprint-backed root configuration."""

    blueprint_path: ClassVar[str]

    @classmethod
    def _get_blueprint_path(cls) -> str:
        """Return and validate the concrete class's blueprint path."""
        path = getattr(cls, "blueprint_path", None)

        if not isinstance(path, str) or not path:
            raise TypeError(
                f"{cls.__name__} must define a non-empty "
                "blueprint_path class variable"
            )

        return path

    @classmethod
    def load(
        cls,
        *,
        defaults: Defaults | None = None,
        normalizer: Callable[[Self], Self] | None = None,
        validator: Callable[[Self], None] | None = None,
    ) -> Self:
        """Load and prepare a fresh immutable configuration snapshot."""
        response = load_one(
            cls._get_blueprint_path()
        )

        config = cls.from_mapping(response)

        if defaults is not None:
            config = apply_defaults(
                config,
                defaults,
            )

        if normalizer is not None:
            config = normalizer(config)

            if not isinstance(config, cls):
                raise TypeError(
                    f"Normalizer for {cls.__name__} returned "
                    f"{type(config).__name__}"
                )

        if validator is not None:
            validator(config)

        return config

    @classmethod
    def change_trigger(cls) -> tuple[str, str]:
        """Return arguments for PyScript's event_trigger decorator."""
        script_service = _script_service_for_blueprint(
            cls._get_blueprint_path()
        )

        return (
            EVENT_SERVICE_REGISTERED,
            (
                f"domain == {SCRIPT_DOMAIN!r} and "
                f"service == {script_service!r}"
            ),
        )