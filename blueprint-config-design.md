# `blueprint-config` Design

**Status:** Draft / working prototype  
**Design version:** 0.5  
**Last revised:** 2026-08-15  
**Canonical format:** Markdown

## 1. Summary

`blueprint-config` provides GUI-backed configuration for Home Assistant PyScript logic by using **script blueprints as configuration instances**.

A script blueprint defines configuration with Home Assistant's native blueprint `input:` and selector syntax. A user creates one or more scripts from that blueprint and edits the values through the normal Home Assistant UI. The configuration script returns those values as script response data.

PyScript then:

1. discovers the script instance by blueprint identity;
2. calls it with `return_response=True`;
3. converts the returned mapping into immutable, typed `attrs` objects; and
4. optionally applies application-defined defaults to unset (`None`) values.

The framework intentionally separates three concerns:

```text
Home Assistant / blueprint     configuration UI and selector constraints
blueprint_config framework     discovery, retrieval, structure, conversion
application                    policy, including how defaults are applied
```

The current prototype has proven the runtime path with a `light_control` configuration from Jupyter.

---

## 2. Goals

The framework should:

- expose PyScript configuration through Home Assistant's existing GUI;
- use Home Assistant's blueprint input/selector syntax rather than inventing a parallel selector DSL;
- provide natural typed access such as `CONFIG.lights` and `light.bright_start`;
- use immutable `attrs` objects as the application-facing configuration representation;
- support exactly-one and, later, multiple script instances based on the same blueprint;
- keep Home Assistant-specific runtime discovery behind a small shared module;
- work naturally from Jupyter and normal PyScript code;
- generate concrete typed Python source when practical so Pylance can infer types without a separate stub;
- use framework converters only where the Python representation should differ from Home Assistant's representation;
- let the application define defaulting policy explicitly instead of inferring policy from field names;
- keep source definition, generated files, and application logic easy to version-control; and
- make rebuild/deployment possible both on the Home Assistant instance and from another machine.

---

## 3. Non-goals

The initial framework is not intended to:

- replace Home Assistant config entries;
- require the consumer to be a PyScript App;
- turn directories under `pyscript/scripts` into normal Python packages;
- implement a second comprehensive copy of Home Assistant's selector validation;
- automatically infer relationships between per-object fields and global default inputs;
- support arbitrarily nested object selectors in the MVP;
- manage deployment transports such as SSH credentials, SCP, rsync, or Samba itself;
- manage secrets; or
- require sophisticated schema migration/versioning before the basic runtime path is proven.

---

## 4. Naming

Use:

```text
Distribution / repository: blueprint-config
Python package:            blueprint_config
CLI command:               blueprint-config
PyScript framework module: blueprint_config
```

The fact that the framework is used by PyScript does not need to be repeated in every identifier.

---

## 5. Current working module layout

The current prototype uses the PyScript `modules` directory:

```text
modules/
└── blueprint_config/
    ├── __init__.py
    ├── blueprint_config.py
    └── light_control/
        ├── __init__.py
        └── config.py
```

The shared package owns generic behavior:

```python
from blueprint_config import load_one, apply_defaults
```

A configuration-specific subpackage owns its generated/derived `attrs` model:

```python
from blueprint_config.light_control import CONFIG, LightConfig
```

This structure has several advantages:

- generated configuration code is importable using PyScript's supported `modules` mechanism;
- each configuration gets its own namespace;
- the application-specific model is separate from generic discovery/runtime code; and
- the same imports work in the PyScript Jupyter kernel.

The generic package may eventually be split internally into files such as `runtime.py`, `converters.py`, and `validators.py`, but that is an implementation organization choice rather than an architectural requirement.

---

## 6. Source organization

Application source does not have to be a PyScript App. A convenient logical-unit layout is:

```text
pyscript/
└── scripts/
    └── light_control/
        ├── light_control.py
        ├── blueprint_config.yaml
        └── #generated/
            └── ...
```

PyScript recursively autoloads `.py` files below `scripts`, so ordinary helper Python files should not be placed there unless they are intended to be independently loaded.

A directory beginning with `#`, such as `#generated`, is useful for generated or development artifacts because PyScript ignores that subtree. This is an optional organizational tool, not a runtime requirement.

Importable runtime modules belong under PyScript's supported `modules` directory.

---

## 7. Canonical configuration definition

The source definition should remain as close as practical to native Home Assistant blueprint syntax. Framework metadata, if needed by the generator, should be kept small and self-contained.

A representative metadata block is:

```yaml
pyscript:
  module: light_control
  instances: one
```

The blueprint configuration itself uses normal Home Assistant input syntax.

The framework should not create a parallel Python selector language such as:

```python
Number(...)
Entity(...)
Time(...)
Object(...)
```

Home Assistant's selector syntax is already the schema language.

---

## 8. Script blueprint as a configuration function

The generated or authored script blueprint has no application behavior. Its job is to collect input values and return them as a mapping.

The working `light_control` pattern is conceptually:

```yaml
blueprint:
  name: Pyscript Light Control
  domain: script
  input:
    lights:
      selector:
        object:
          multiple: true
          fields:
            light:
              required: true
              selector:
                entity:
                  filter:
                    - domain: light
            button:
              selector:
                device:
            brightness_high:
              selector:
                number:
                  min: 0
                  max: 255
            brightness_low:
              selector:
                number:
                  min: 0
                  max: 255
            bright_start:
              selector:
                time:
            bright_end:
              selector:
                time:

    defaults:
      name: Default settings
      collapsed: true
      input:
        default_brightness_high:
          default: 150
          selector:
            number:
              min: 0
              max: 255
        default_brightness_low:
          default: 10
          selector:
            number:
              min: 0
              max: 255
        default_bright_start:
          default: "07:00:00"
          selector:
            time:
        default_bright_end:
          default: "21:00:00"
          selector:
            time:

sequence:
  - variables:
      result:
        lights: !input lights
        default_brightness_high: !input default_brightness_high
        default_brightness_low: !input default_brightness_low
        default_bright_start: !input default_bright_start
        default_bright_end: !input default_bright_end

  - stop: Return blueprint configuration
    response_variable: result
```

The service response is therefore already the application configuration source.

---

## 9. Input sections versus structured values

Blueprint input sections are UI grouping only. They do not create nested response objects.

For example, the `defaults:` input section above produces individual response keys such as:

```python
response["default_brightness_high"]
response["default_bright_start"]
```

The section itself is not returned as a nested `defaults` object.

Actual nested data comes from selectors whose value is structured, especially the `object` selector.

For the `lights` object selector with `multiple: true`, the returned value is naturally represented as:

```python
tuple[LightConfig, ...]
```

---

## 10. MVP restriction: no nested object selectors

Home Assistant may permit an `object` selector field to contain another `object` selector, but supporting arbitrary nesting complicates:

- class generation;
- optionality;
- default application;
- recursive conversion;
- naming; and
- testing.

The MVP should therefore explicitly reject an object field whose selector is itself `object`.

Supported:

```text
top-level blueprint input
    └── object selector
            ├── entity
            ├── device
            ├── number
            ├── time
            └── other non-object selectors
```

Initially unsupported:

```text
object
    └── object
```

Generation should fail early with a useful message identifying the nested field. Recursive object support can be added later if a compelling real-world use case appears.

---

## 11. Runtime discovery and `load_one`

The generic framework discovers configuration scripts by blueprint identity rather than by script entity naming convention.

Home Assistant currently provides:

```python
from homeassistant.components.script import scripts_with_blueprint
```

Conceptually:

```python
entity_ids = scripts_with_blueprint(hass, blueprint_path)
```

For one discovered entity, the runtime obtains the script's callable service name from the entity registry and calls it with:

```python
response = service.call(
    "script",
    registry_entry.unique_id,
    return_response=True,
)
```

The generic API is approximately:

```python
T = TypeVar("T")


def load_one(
    blueprint_path: str,
    factory: Callable[[Mapping[str, Any]], T],
) -> T | None:
    ...
```

Responsibilities of `load_one()`:

- locate script instances based on the blueprint path;
- enforce singleton cardinality policy;
- resolve the callable script service;
- call it synchronously for its response;
- ensure the response is mapping-like; and
- pass the mapping to the configuration-specific factory.

It should know nothing about `LightConfig`, brightness, schedules, or any other application fields.

### 11.1 Zero-instance behavior

The current prototype returns `None` when no script instance exists so a consumer can terminate without constructing a configuration.

Earlier design discussion favored treating zero instances as a configuration error with a Home Assistant notification. The final policy should be settled after the prototype lifecycle is tested in a normal PyScript consumer.

### 11.2 Multiple singleton instances

When a singleton configuration discovers more than one matching script, the framework must not choose arbitrarily. This is an error and should eventually produce an actionable Home Assistant notification as well as a log message.

---

## 12. `attrs` configuration models

The configuration-specific module defines concrete frozen `attrs` classes.

For the light-control prototype:

```python
import datetime as dt

from attrs import field, frozen


@frozen
class LightConfig:
    light: str
    button: str | None = None
    brightness_high: float | None = None
    brightness_low: float | None = None
    bright_start: dt.time | None = field(
        default=None,
        converter=to_time,
    )
    bright_end: dt.time | None = field(
        default=None,
        converter=to_time,
    )


@frozen
class LightControlConfig:
    lights: tuple[LightConfig, ...]
    default_brightness_high: float
    default_brightness_low: float
    default_bright_start: dt.time = field(converter=to_time)
    default_bright_end: dt.time = field(converter=to_time)
```

The factory is intentionally mechanical:

```python
def _from_response(data: Mapping[str, Any]) -> LightControlConfig:
    return LightControlConfig(
        lights=tuple(LightConfig(**item) for item in data["lights"]),
        default_brightness_high=data["default_brightness_high"],
        default_brightness_low=data["default_brightness_low"],
        default_bright_start=data["default_bright_start"],
        default_bright_end=data["default_bright_end"],
    )
```

This code is a good candidate for generation because almost all of it is derived directly from the blueprint selector structure.

---

## 13. Optionality and `required`

A selector describes the non-`None` value type, but configuration fields may be unset unless the schema/application guarantees otherwise.

For an optional object field, the generated representation should normally be:

```python
button: str | None = None
brightness_high: float | None = None
bright_start: dt.time | None = None
```

For a field marked:

```yaml
required: true
```

the generated application-facing type should be non-optional:

```python
light: str
```

The generated class should also defensively enforce the framework-level invariant that a required value is not `None`.

A generic framework validator is sufficient:

```python
@pyscript_compile
def not_none(instance, attribute, value):
    if value is None:
        raise ValueError(f"{attribute.name} is required")
```

This is intentionally narrower than revalidating the selector itself. For example, the framework does not need to repeat the `0..255` range constraint of a brightness selector.

---

## 14. Conversion helpers

Converters belong in the shared `blueprint_config` module rather than being repeated in each generated configuration module.

For time selectors:

```python
@pyscript_compile
def to_time(
    value: str | dt.time | None,
) -> dt.time | None:
    if value is None or isinstance(value, dt.time):
        return value
    return dt.time.fromisoformat(value)
```

A generated configuration module can then simply use:

```python
bright_start: dt.time | None = field(
    default=None,
    converter=to_time,
)
```

Initial conversion philosophy:

```text
time      -> datetime.time
date      -> datetime.date          (when implemented)
datetime  -> datetime.datetime      (when implemented)
number    -> HA numeric value       no duplicate range validation
entity    -> str / None
device    -> str / None
text      -> str / None
boolean   -> bool / None as appropriate
```

Converters are representation transformations, not a second selector-validation system.

---

## 15. Application-defined defaults

### 15.1 Why defaults are application policy

An object selector does not provide a convenient field-level default mechanism for every element in a repeated object. Global defaults can instead be represented as ordinary blueprint inputs, preferably grouped in a collapsed input section.

The framework should **not** infer that:

```text
brightness_high
```

is related to:

```text
default_brightness_high
```

by naming convention. Such inference becomes fragile as schemas grow and would turn the framework into a policy engine.

Instead, the application explicitly declares which configuration type and fields receive defaults.

### 15.2 Type-keyed defaults map

For the light-control application:

```python
LIGHT_DEFAULTS = {
    LightConfig: {
        "brightness_high": CONFIG.default_brightness_high,
        "brightness_low": CONFIG.default_brightness_low,
        "bright_start": CONFIG.default_bright_start,
        "bright_end": CONFIG.default_bright_end,
    }
}
```

This is compact, explicit, and type-directed.

### 15.3 `apply_defaults()`

The shared framework provides a recursive helper:

```python
apply_defaults(inp, defaults)
```

Its semantics are:

1. recurse through tuples;
2. recurse through fields of `attrs` objects;
3. find a defaults dictionary keyed by the object's exact type;
4. replace only fields whose current value is `None`; and
5. preserve immutability by returning evolved objects.

A representative implementation is:

```python
T = TypeVar("T")
Defaults = dict[type, dict[str, Any]]


@pyscript_compile
def apply_defaults(inp: T, defaults: Defaults) -> T:
    if isinstance(inp, tuple):
        return tuple(apply_defaults(x, defaults) for x in inp)

    if not attrs.has(type(inp)):
        return inp

    changes: dict[str, Any] = {}

    # Recurse first so defaults can also be applied below this object.
    for attribute in attrs.fields(type(inp)):
        value = getattr(inp, attribute.name)
        new_value = apply_defaults(value, defaults)
        if new_value is not value:
            changes[attribute.name] = new_value

    # Then apply defaults for this exact attrs type.
    for name, default in defaults.get(type(inp), {}).items():
        value = changes.get(name, getattr(inp, name))
        if value is None:
            changes[name] = default

    return attrs.evolve(inp, **changes) if changes else inp
```

`attrs.evolve()` is appropriate because it creates a new instance of the same frozen attrs class and changes only the keyword fields explicitly supplied in `changes`.

The important defaulting rule is:

```text
None -> configured default
0    -> remains 0
False -> remains False
other explicit value -> remains unchanged
```

The function does not use truthiness to decide whether a value is missing.

### 15.4 Application call site

The resulting application code is deliberately small:

```python
LIGHT_DEFAULTS = {
    LightConfig: {
        "brightness_high": CONFIG.default_brightness_high,
        "brightness_low": CONFIG.default_brightness_low,
        "bright_start": CONFIG.default_bright_start,
        "bright_end": CONFIG.default_bright_end,
    }
}

CONFIG_LIGHTS = apply_defaults(CONFIG, LIGHT_DEFAULTS).lights
```

Applying defaults at the root allows the helper to find matching configuration objects anywhere in the supported configuration tree. The application can still keep the original `CONFIG` object for inspection/debugging.

### 15.5 Exact type matching

Defaults should initially be keyed by exact attrs type:

```python
defaults.get(type(inp), {})
```

rather than by `isinstance()` inheritance matching. Generated configuration classes are not expected to form a class hierarchy, and exact matching is more predictable.

---

## 16. Validation philosophy

The framework should remain deliberately thin.

### 16.1 Do not duplicate selector constraints

If Home Assistant presents a number selector with:

```yaml
min: 0
max: 255
```

`blueprint_config` should not also generate `attrs.validators.ge(0)` and `le(255)` merely to repeat the same rule.

Likewise, it should not replicate select options, entity filters, or device filters as a second validation language.

### 16.2 Framework-level invariants are different

A few checks belong to the framework because they express its own contract rather than selector semantics:

- singleton/multiple-instance cardinality;
- script response must be mapping-like;
- required generated fields must not be `None`;
- conversion to richer Python representations must succeed;
- nested object selectors are rejected in the MVP; and
- generated/runtime schema mismatch should fail clearly.

### 16.3 Backend selector validation is not assumed to be comprehensive

The Home Assistant UI strongly constrains normal configuration entry, but the blueprint backend does not necessarily run every selector validator against every stored value.

The framework should therefore avoid claiming that every selector constraint has been revalidated at runtime. The design still avoids reproducing the selector schema unless a concrete failure mode demonstrates a need.

---

## 17. Initial selector-to-Python mapping

A conservative initial mapping is:

| Selector | Generated representation |
|---|---|
| `boolean` | `bool | None` unless guaranteed |
| `number` | `float | None` unless guaranteed |
| `text` | `str | None` unless guaranteed |
| `time` | `datetime.time | None`, via `to_time` |
| `date` | `datetime.date | None`, future converter |
| `datetime` | `datetime.datetime | None`, future converter |
| `entity` | `str | None`; collection form when `multiple` |
| `device` | `str | None`; collection form when `multiple` |
| `area` | `str | None`; collection form when `multiple` |
| `select` | `str | None`; possibly `Literal[...]` later |
| top-level `object` with `fields` | generated `attrs` class |
| `object` with `multiple: true` | `tuple[GeneratedClass, ...]` |
| nested `object` field | unsupported in MVP |
| unknown selector | `Any` or explicit unsupported error; still open |

A field marked `required: true` can narrow its generated type to non-optional and receive the shared `not_none` validator.

---

## 18. Concrete generated Python versus `.pyi`

The working prototype generates or hand-authors **concrete typed Python classes** in `config.py`.

Because that source contains real annotations such as:

```python
@frozen
class LightConfig:
    light: str
    brightness_high: float | None = None
```

Pylance/Pyright can infer the API directly from the `.py` module.

Therefore a separate `.pyi` is **not required for the MVP**.

A `.pyi` may become useful later if:

- classes are dynamically manufactured rather than emitted as source;
- the runtime implementation intentionally hides substantial metaprogramming; or
- a cleaner public static interface is desired.

Until then, generating both `.py` and `.pyi` would duplicate the same information.

---

## 19. Jupyter workflow

The current prototype is exercised in `blueprint_play.ipynb` using the PyScript kernel.

Typical usage is:

```python
from blueprint_config import apply_defaults
from blueprint_config.light_control import CONFIG, LightConfig
```

The raw `CONFIG.lights` tuple contains values returned by Home Assistant, including `None` for fields left unset.

The application can define its defaults map and create its effective light configuration with:

```python
CONFIG_LIGHTS = apply_defaults(CONFIG, LIGHT_DEFAULTS).lights
```

The same imports should be usable from production PyScript code.

If configuration modules are regenerated while a Jupyter kernel is still running, normal Python/PyScript module caching may require a reload or kernel restart during development.

---

## 20. Generation

Generation should be a normal Python build/configuration step, not part of Home Assistant startup.

Possible CLI forms:

```bash
blueprint-config generate path/to/blueprint_config.yaml
```

or:

```bash
python -m blueprint_config generate path/to/blueprint_config.yaml
```

A recursive directory mode may later discover `blueprint_config.yaml` files automatically.

The generator should derive everything it reasonably can from the definition and small framework metadata so extra command-line arguments are unnecessary for normal use.

Likely generator responsibilities:

1. read the source YAML;
2. validate framework metadata;
3. preserve/pass through native Home Assistant blueprint input syntax;
4. reject unsupported nested object selectors;
5. derive concrete attrs classes and field annotations;
6. attach shared converters/validators where needed;
7. generate the script sequence that returns all configuration values;
8. generate the configuration-specific Python package/module; and
9. write/install generated files to their configured destinations.

---

## 21. `#generated` directory

A source-local `#generated/` directory remains useful as a **build output/staging area**.

For example:

```text
scripts/light_control/
    light_control.py
    blueprint_config.yaml
    #generated/
        light_control.yaml
        light_control/
            __init__.py
            config.py
```

Possible uses:

- inspect generated output;
- diff generation changes in Git;
- stage files for deployment;
- keep generated `.py` out of PyScript's recursive `scripts` autoloader; and
- debug what will be installed.

Generated files are not the canonical source. The YAML definition and application source are canonical.

---

## 22. Distribution model

Distribution should normally ship **source plus the configuration definition and rebuild on the recipient system**.

This supersedes the earlier “build once, install many without regeneration” idea.

Reason: a recipient is likely to want to adjust selectors for their own environment, for example:

```yaml
integration: mqtt
manufacturer: SONOFF
model_id: SNZB-01P
```

A rebuild naturally incorporates those local selector changes into the installed blueprint and generated configuration model.

A distributable project therefore primarily needs:

```text
application source
blueprint_config.yaml
```

Generated files may be included for reference or convenience, but they are not authoritative and should be expected to be rebuilt after schema changes.

---

## 23. Build versus deployment

The generator should separate **what files belong where** from **how bytes reach the Home Assistant system**.

### 23.1 Running on the Home Assistant system

When the tool runs where `/config` is directly accessible, it can write the live destinations directly, for example:

```text
/config/blueprints/script/blueprint_config/...
/config/pyscript/modules/blueprint_config/...
```

### 23.2 Running on a laptop/workstation

When the tool runs elsewhere, it can build an install-shaped tree rooted at a staging directory:

```text
#generated/homeassistant/
    blueprints/
        script/
            blueprint_config/
                ...
    pyscript/
        modules/
            blueprint_config/
                ...
```

Deployment can then use any filesystem/transport mechanism the user prefers:

- mounted Samba share;
- SSHFS;
- `scp`;
- `rsync` over SSH; or
- another copy/synchronization mechanism.

The MVP should **not** own SSH keys, passwords, host verification, or remote transport configuration. It should install to a filesystem root or create an install-shaped tree and let external tools transport it.

---

## 24. Error reporting

Errors should be actionable and, where user intervention is needed, eventually surfaced through Home Assistant notifications as well as logs.

Initial error cases include:

- malformed framework metadata;
- unsupported nested object selector;
- zero/multiple singleton instances according to final cardinality policy;
- missing entity-registry entry for a discovered script;
- script service call failure;
- non-mapping response;
- required field missing or `None`;
- converter failure; and
- stale/incompatible generated code versus returned response.

---

## 25. Current prototype status

The runtime proof of concept currently demonstrates:

- a real script blueprint returning configuration data;
- discovery by blueprint path using `scripts_with_blueprint()`;
- service resolution through the script entity registry entry;
- `return_response=True` retrieval;
- a generic `load_one()` adapter;
- a configuration-specific `light_control` subpackage;
- frozen `LightConfig` and `LightControlConfig` attrs objects;
- time-string conversion to `datetime.time`;
- `CONFIG` import from Jupyter;
- repeated light objects represented as a tuple;
- application-defined global default values returned through ordinary blueprint inputs; and
- a compact type-keyed defaults policy suitable for `apply_defaults()`.

The next generic runtime primitive to finish is `apply_defaults()` in the shared `blueprint_config` module.

---

## 26. MVP implementation plan

1. Clean up and type the current `load_one()` implementation.
2. Move generic `to_time` and `not_none` helpers into the shared `blueprint_config` package.
3. Implement and test recursive `apply_defaults()` using `attrs.evolve()`.
4. Use the current light-control configuration as the reference vertical slice.
5. Define the initial selector-to-Python type mapping.
6. Define generation rules for optional versus `required: true` object fields.
7. Explicitly reject nested object selectors.
8. Generate concrete typed `config.py` source for the light-control example.
9. Generate/install the corresponding script blueprint.
10. Test imports and default application from both Jupyter and a normal PyScript consumer.
11. Add singleton-cardinality notifications/error handling.
12. Add `instances: many` only after singleton behavior is stable.
13. Add the CLI/build/deployment path after runtime generation is proven.
14. Revisit `.pyi` only if concrete generated source proves insufficient for tooling.

---

## 27. Open design questions

### 27.1 Zero singleton instances

Should `load_one()`:

```text
return None
```

so the consumer can quietly terminate, or should zero instances always produce a Home Assistant configuration notification?

The prototype currently returns `None`.

### 27.2 Unknown selectors

If the generator encounters a selector it does not understand, should it:

- pass it through and type the value as `Any`; or
- fail generation with an explicit unsupported-selector error?

### 27.3 Multiple instances

For `instances: many`, should each result contain only the generated configuration object, or should framework metadata such as the source script entity ID be exposed separately?

### 27.4 Refresh semantics

Is explicit reload/restart after configuration edits sufficient, or should the framework eventually react automatically when configuration scripts are reloaded?

### 27.5 Generated artifact manifest

Would a small manifest of generated files and target paths help installation, cleanup, and deployment without making the build system unnecessarily elaborate?

### 27.6 Nested objects

Nested `object` selectors are deliberately unsupported in the MVP. If a real use case appears, recursion can be added later without changing the basic configuration-instance concept.

---

## 28. Design principles

1. **Use Home Assistant's configuration language where it already exists.**
2. **Keep framework metadata small.**
3. **Separate Home Assistant configuration from application policy.**
4. **Use immutable typed attrs objects at the application boundary.**
5. **Use converters for representation changes, not duplicate validation.**
6. **Use `required` to express a non-`None` framework invariant.**
7. **Apply defaults explicitly by type rather than by naming convention.**
8. **Replace only `None`; never treat falsy values as missing.**
9. **Keep generic behavior in `blueprint_config`; keep schema-specific classes in configuration subpackages.**
10. **Prefer concrete generated Python source before adding `.pyi` complexity.**
11. **Disallow pathological complexity until a real use case requires it.**
12. **Never silently choose among ambiguous singleton instances.**
13. **Keep Home Assistant internal API dependencies behind narrow adapters.**
14. **Keep generation out of the Home Assistant startup/runtime path.**
15. **Treat `#generated` as staging/build output rather than canonical source.**
16. **Distribute source/configuration definitions and rebuild when selectors are customized.**
17. **Separate generation/install layout from transport/deployment mechanics.**
18. **Keep Jupyter and production imports as similar as possible.**
19. **Prefer a small understandable framework over a comprehensive second configuration system.**

---

## 29. Recommended next step

Finish the shared defaulting helper and make the current light-control example the reference behavior:

```python
LIGHT_DEFAULTS = {
    LightConfig: {
        "brightness_high": CONFIG.default_brightness_high,
        "brightness_low": CONFIG.default_brightness_low,
        "bright_start": CONFIG.default_bright_start,
        "bright_end": CONFIG.default_bright_end,
    }
}

CONFIG_LIGHTS = apply_defaults(CONFIG, LIGHT_DEFAULTS).lights
```

Then verify three cases for every defaulted field:

```text
None            -> default is applied
explicit value  -> explicit value wins
falsy value     -> falsy value is preserved
```

Once that behavior is solid, the generator can emit the concrete `attrs` model and conversion factory mechanically from the blueprint input schema.
