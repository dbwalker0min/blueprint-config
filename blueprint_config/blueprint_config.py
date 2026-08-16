from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from stubs.pyscript_builtins import pyscript_compile
from homeassistant.components.script import scripts_with_blueprint
from homeassistant.helpers import entity_registry as er
from stubs.pyscript_builtins import hass, service
import attrs


T = TypeVar("T")

Defaults = dict[type, dict[str, Any]]

@pyscript_compile
def apply_defaults(inp: T, defaults: Defaults) -> T:
    """Recursively apply defaults to None fields of attrs objects."""

    if isinstance(inp, tuple):
        return tuple(
            apply_defaults(item, defaults)
            for item in inp
        )

    # It's not an attrs type, so just return it
    if not attrs.has(type(inp)):
        return inp


    # It's got to be an attrs type here.
    
    changes = {}
    
    # First recursively process attributes.
    for attribute in attrs.fields(type(inp)):
        value = getattr(inp, attribute.name)
        new_value = apply_defaults(value, defaults)

        if new_value is not value:
            changes[attribute.name] = new_value

    # Then apply defaults belonging to this attrs type.
    object_defaults = defaults.get(type(inp), {})

    for name, default in object_defaults.items():
        # Use the recursively updated value if there is one.
        value = changes.get(name, getattr(inp, name))

        if value is None:
            changes[name] = default

    if not changes:
        return inp

    return attrs.evolve(inp, **changes) 

def load_one(
    blueprint_path: str,
    factory: Callable[[Mapping[str, Any]], T]
) -> T | None:
    """Load exactly one enabled script instance of a blueprint."""

    entity_ids = scripts_with_blueprint(hass, blueprint_path)

    n_entities = len(entity_ids)
    
    # Return None to indcate there are no configurations so the script can terminate
    if n_entities == 0:
        return None

    if n_entities > 1:
        raise ValueError(f'Too many ({n_entities}) scripts use this blueprint.')

    # This is the only entity...
    entity_id = entity_ids[0]

    registry_entry = er.async_get(hass).async_get(entity_id)
    if registry_entry is None:
        raise RuntimeError(
            f"No entity registry entry for {entity_id}"
        )

    # A script's service name is its immutable unique_id, not necessarily
    # the current entity_id.
    response = service.call(
        "script",
        registry_entry.unique_id,
        return_response=True,
    )

    if not isinstance(response, Mapping):
        raise TypeError(
            f"{entity_id} returned {type(response).__name__}; "
            "expected a mapping"
        )

    return factory(response)