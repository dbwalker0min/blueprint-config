# `blueprint-config` Design

**Status:** Draft / working prototypes  
**Design version:** 0.6  
**Last revised:** 2026-08-17  
**Canonical format:** Markdown

## 1. Summary

`blueprint-config` provides GUI-backed configuration for Home Assistant PyScript logic by using **script blueprints as configuration instances**.

A Home Assistant script blueprint defines configuration with native blueprint `input:` and selector syntax. A user creates a script from that blueprint and edits the values through the normal Home Assistant UI. The script returns those values as response data.

The framework then:

1. discovers the configuration script by blueprint identity;
2. calls it with `return_response=True`;
3. converts the returned mapping into immutable typed `attrs` objects;
4. optionally applies application-defined defaults;
5. optionally normalizes the resulting configuration;
6. optionally validates application-level invariants; and
7. returns an immutable configuration snapshot to the application.

The configuration **class** carries blueprint identity and lifecycle behavior. Configuration **instances** are replaceable immutable snapshots; they are not singletons.

The current architecture has been driven by two practical vertical slices:

- `light_control`, which established repeated object selectors, optional fields, representation converters, and recursive default application; and
- `solar_discharge`, which established repeated schedule entries, duration conversion, configuration-change detection, normalization/validation hooks, and the class-based configuration API.

---

## 2. Design method: work backward from practical examples

The project intentionally develops the runtime contract before implementing the generator.

The process is:

```text
real application need
      ↓
hand-authored Home Assistant blueprint
      ↓
inspect actual stored/returned values
      ↓
hand-author the Python API we wish the generator had emitted
      ↓
exercise it from Jupyter / PyScript
      ↓
extract generic framework behavior
      ↓
only then implement generator rules
```

This approach is a design principle, not just a prototyping convenience. It avoids committing the generator to abstractions that look elegant in isolation but are awkward when used with the actual Home Assistant UI or PyScript runtime.

The generator should therefore be viewed as a **mechanical producer of already-proven outputs**, not as the place where the object model is invented.

---

## 3. Goals

The framework should:

- expose PyScript configuration through Home Assistant's existing GUI;
- use Home Assistant blueprint input/selector syntax rather than inventing a parallel selector DSL;
- provide natural statically typed access to configuration data;
- use immutable `attrs` objects at the application boundary;
- allow nested/repeated configuration objects to be represented naturally;
- centralize structural construction in generic runtime code rather than generate bespoke factories for every schema;
- keep Home Assistant-specific discovery behind a small adapter;
- provide explicit configuration refresh when the backing script changes;
- support application-defined defaults, normalization, and validation without making those policies part of the generator;
- use shared converters only when the Python representation should differ from Home Assistant's representation;
- work naturally from Jupyter and normal PyScript code;
- generate concrete typed Python source so Pylance/Pyright can infer the API directly;
- keep source definitions and generated output easy to version-control; and
- keep generation/install layout independent of transport/deployment mechanics.

---

## 4. Non-goals

The initial framework is not intended to:

- replace Home Assistant config entries;
- require the consumer to be a PyScript App;
- invent a second comprehensive selector-validation system;
- infer application semantics from field names;
- infer which fields should default to which other fields;
- own semantic rules such as whether discharge schedule ranges may overlap;
- mutate configuration objects in place;
- cache one global singleton configuration instance;
- manage secrets;
- own SSH credentials, SCP, rsync, or other deployment transport configuration; or
- solve every possible Home Assistant selector shape before a practical use case exists.

---

## 5. Naming

Use:

```text
Distribution / repository: blueprint-config
Python package:            blueprint_config
CLI command:               blueprint-config
PyScript framework module: blueprint_config
```

The fact that the framework is used by PyScript does not need to be repeated in every identifier.

---

## 6. Current module layout

The working runtime is organized as an importable PyScript module package:

```text
modules/
└── blueprint_config/
    ├── __init__.py
    ├── blueprint_config.py
    ├── light_control/
    │   ├── __init__.py
    │   └── config.py
    └── solar_discharge/
        ├── __init__.py
        └── config.py
```

The shared package owns generic behavior such as:

```python
ConfigObject
BlueprintConfig
load_one
apply_defaults
to_time
to_timedelta
not_none
blueprint_from_script_service
```

Each configuration-specific subpackage owns generated schema-specific classes such as:

```python
LightConfig
LightControlConfig
ScheduleConfig
SolarDischargeConfig
```

This arrangement keeps generated configuration code importable through PyScript's supported `modules` mechanism and makes the same API available to the PyScript Jupyter kernel.

The shared package may later be split internally into `runtime.py`, `converters.py`, `validators.py`, etc.; that is an implementation choice rather than an architectural requirement.

---

## 7. Source organization

Application source need not be a PyScript App. One useful source layout is:

```text
pyscript/
└── scripts/
    └── solar_discharge/
        ├── solar_discharge.py
        ├── blueprint_config.yaml
        └── #generated/
            └── ...
```

PyScript recursively autoloads `.py` files below `scripts`, so ordinary helper modules should not be placed there unless they are intended to be independently loaded.

A leading-`#` directory such as `#generated` is useful for staging generated output because PyScript ignores that subtree. It is optional and is not part of the runtime API.

Importable generated/runtime modules belong under `pyscript/modules`.

---

## 8. Canonical configuration definition

The configuration definition should remain as close as practical to native Home Assistant blueprint syntax. Framework metadata, if required by the generator, should remain small.

A representative framework metadata block remains:

```yaml
pyscript:
  module: solar_discharge
  instances: one
```

The configuration itself should use normal Home Assistant blueprint syntax and selectors. The framework should not create a parallel Python DSL such as:

```python
Number(...)
Entity(...)
Time(...)
Object(...)
```

Home Assistant already provides the configuration language and GUI.

YAML anchors and aliases are encouraged where they make repetitive selector definitions easier to maintain. Generator code must avoid relying on alias object identity and should copy structures before mutating them.

---

## 9. Script blueprint as a configuration function

A configuration blueprint has no application behavior. Its purpose is to collect input values and return them as script response data.

Conceptually:

```yaml
sequence:
  - variables:
      result:
        pw_op_mode: !input pw_op_mode
        pw_export_mode: !input pw_export_mode
        schedule: !input schedule

  - stop: Return blueprint configuration
    response_variable: result
```

The script acts like a GUI-backed configuration function:

```text
PyScript ---- call ----> configuration script
         <--- mapping ---
```

The generator should synthesize this return sequence mechanically when possible.

---

## 10. Input sections versus structured values

Home Assistant blueprint input sections are UI grouping only. Inputs within a section are still globally named blueprint inputs.

Sections therefore should not automatically imply nested application data.

Actual nested/repeated application data should normally come from selectors whose **values are structured**, particularly `object` selectors and `object` selectors with `multiple: true`.

A generated return mapping may deliberately introduce useful nesting, but that is an explicit output decision rather than an assumption about Home Assistant section semantics.

---

## 11. Runtime object model

The current design separates ordinary configuration objects from root blueprint-backed configuration objects.

```text
ConfigObject
    ↑
    ├── ScheduleConfig
    ├── LightConfig
    └── BlueprintConfig (ABC)
            ↑
            ├── LightControlConfig
            └── SolarDischargeConfig
```

### 11.1 `ConfigObject`

`ConfigObject` provides generic **structural construction** from a mapping.

Its core API is conceptually:

```python
class ConfigObject:
    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Self:
        ...
```

`from_mapping()` recursively uses the generated attrs field annotations to construct nested `ConfigObject` instances and tuples of them.

It does **not** need to know blueprint paths, Home Assistant services, defaults, or application semantics.

### 11.2 `BlueprintConfig`

`BlueprintConfig` is an `ABC` and the lifecycle-aware root configuration base class.

Conceptually:

```python
class BlueprintConfig(ConfigObject, ABC):
    blueprint_path: ClassVar[str]

    @classmethod
    def load(... ) -> Self:
        ...

    @classmethod
    def change_trigger(cls) -> tuple[str, str]:
        ...
```

Only root configuration classes inherit from `BlueprintConfig`. Nested classes such as `ScheduleConfig` inherit only from `ConfigObject`.

The concrete root class declares the blueprint identity:

```python
@frozen
class SolarDischargeConfig(BlueprintConfig):
    blueprint_path = "pyscript/solar_discharge.yaml"
    ...
```

The generator must ensure each concrete `BlueprintConfig` subclass defines a valid blueprint path. Python's ABC machinery does not directly enforce a class variable, so this can be enforced by generation and/or a runtime subclass/load check.

### 11.3 Not a singleton

`SolarDischargeConfig` is a persistent **type-level handle/factory**, not a singleton instance.

Each call to:

```python
SolarDischargeConfig.load()
```

returns a newly constructed immutable snapshot of the current configuration.

After an edit:

```python
old = CONFIG
CONFIG = SolarDischargeConfig.load()

assert old is not CONFIG
```

This replacement model is intentional.

---

## 12. Generic recursive `from_mapping()`

The earlier prototype generated a bespoke factory such as:

```python
def _from_response(data):
    return LightControlConfig(
        lights=tuple(LightConfig(**item) for item in data["lights"]),
        ...
    )
```

That construction is almost entirely derivable from the generated types, so it should be generalized.

`ConfigObject.from_mapping()` should:

1. inspect `attrs.fields(cls)`;
2. obtain each field's value from the incoming mapping;
3. inspect the field's generated type annotation;
4. recursively call `from_mapping()` for nested `ConfigObject` types;
5. recursively construct tuples such as `tuple[ScheduleConfig, ...]`; and
6. pass scalar values through to the attrs constructor.

Scalar representation conversion remains the responsibility of attrs converters.

Conceptually:

```python
@frozen
class ScheduleConfig(ConfigObject):
    month: str
    start_time: dt.time = field(converter=to_time)
    duration: dt.timedelta = field(converter=to_timedelta)


@frozen
class SolarDischargeConfig(BlueprintConfig):
    blueprint_path = "pyscript/solar_discharge.yaml"

    pw_op_mode: str
    pw_export_mode: str
    schedule: tuple[ScheduleConfig, ...]
```

Given:

```python
{
    "pw_op_mode": "select.powerwall_operation_mode",
    "pw_export_mode": "select.powerwall_allow_export",
    "schedule": [
        {
            "month": "June",
            "start_time": "18:00:00",
            "duration": {
                "hours": 0,
                "minutes": 45,
                "seconds": 0,
            },
        }
    ],
}
```

`SolarDischargeConfig.from_mapping()` can construct the entire object tree without generated schema-specific factory code.

Implementation will likely use `typing.get_origin()` / `typing.get_args()` or equivalent type inspection. The supported recursive type forms should remain deliberately small and explicit.

---

## 13. Nested object selectors

Earlier design versions explicitly rejected nested object selectors because every level appeared to require custom generated construction logic.

The generic `ConfigObject.from_mapping()` design changes that assessment.

Nested object selectors are no longer considered an architectural problem: the generator can recursively emit `ConfigObject` subclasses, while the runtime constructor can recursively instantiate them using the generated annotations.

For example:

```python
@frozen
class WeekendConfig(ConfigObject):
    start: dt.time = field(converter=to_time)
    duration: dt.timedelta = field(converter=to_timedelta)


@frozen
class ScheduleConfig(ConfigObject):
    weekday_start: dt.time = field(converter=to_time)
    weekend: WeekendConfig | None = None
```

Nested selector support still needs a practical vertical-slice test before being declared complete. The initial generator may implement simpler shapes first, but nested objects should no longer be rejected as a fundamental design rule.

---

## 14. Runtime discovery and raw retrieval

The shared runtime discovers configuration scripts by blueprint identity rather than by script entity naming convention.

Home Assistant currently provides helpers such as:

```python
from homeassistant.components.script import scripts_with_blueprint
```

Conceptually:

```python
entity_ids = scripts_with_blueprint(hass, blueprint_path)
```

For a discovered entity, the callable script service is resolved from the entity registry entry's immutable `unique_id` and called with:

```python
response = service.call(
    "script",
    registry_entry.unique_id,
    return_response=True,
)
```

With recursive construction moved to `ConfigObject`, the generic retrieval primitive can be narrower than the original factory-based prototype:

```python
def load_one(
    blueprint_path: str,
) -> Mapping[str, Any] | None:
    ...
```

Its responsibilities are only:

- discover scripts using the blueprint path;
- enforce singleton cardinality policy;
- resolve the script service;
- call it synchronously;
- ensure the response is mapping-like; and
- return the raw mapping.

`BlueprintConfig.load()` then calls `cls.from_mapping(response)`.

### 14.1 Cardinality

For `instances: one`, more than one matching script is always an error; the framework must never choose arbitrarily.

The final zero-instance behavior remains open. The prototype has returned `None`, while an exactly-one contract arguably favors an actionable configuration error/notification.

---

## 15. Representation converters

Converters belong in shared framework code rather than being repeated in generated modules.

### 15.1 Time

```python
@pyscript_compile
def to_time(
    value: str | dt.time | None,
) -> dt.time | None:
    if value is None or isinstance(value, dt.time):
        return value
    return dt.time.fromisoformat(value)
```

### 15.2 Duration

Home Assistant duration selectors return mappings. Application code generally wants `datetime.timedelta`:

```python
@pyscript_compile
def to_timedelta(
    value: Mapping[str, int] | dt.timedelta | None,
) -> dt.timedelta | None:
    if value is None or isinstance(value, dt.timedelta):
        return value
    return dt.timedelta(**value)
```

### 15.3 Initial conversion philosophy

```text
time      -> datetime.time
duration  -> datetime.timedelta
date      -> datetime.date          when implemented
datetime  -> datetime.datetime      when implemented
number    -> HA numeric value       no duplicate range validation
entity    -> str / None
device    -> str / None
text      -> str / None
boolean   -> bool / None as appropriate
```

Converters transform representation; they do not duplicate Home Assistant selector validation.

---

## 16. Optionality and `required`

A selector describes a nominal non-`None` value type, but fields may be absent/unset unless the generated schema guarantees otherwise.

Optional fields should normally be represented as optional:

```python
label: str | None = None
weekend: bool | None = None
```

A field declared with:

```yaml
required: true
```

can be represented as non-optional:

```python
start_time: dt.time
```

and can use a shared defensive validator such as `not_none` to protect the runtime promise.

The framework should not duplicate selector constraints such as number ranges, select choices, or entity filters merely because a field is required.

---

## 17. Application-defined defaults

Defaults are application policy, not schema inference.

The framework should not infer that:

```text
brightness_high
```

is related to:

```text
default_brightness_high
```

by name.

Instead, applications use a type-keyed defaults map:

```python
Defaults = dict[type, dict[str, Any]]

LIGHT_DEFAULTS = {
    LightConfig: {
        "brightness_high": raw.default_brightness_high,
        "brightness_low": raw.default_brightness_low,
        "bright_start": raw.default_bright_start,
        "bright_end": raw.default_bright_end,
    }
}
```

### 17.1 `apply_defaults()`

The shared recursive helper:

```python
apply_defaults(inp, defaults)
```

has these semantics:

1. recurse through tuples;
2. recurse through attrs object fields;
3. find defaults by the object's exact type;
4. replace only fields whose current value is `None`; and
5. preserve immutability using `attrs.evolve()`.

The important rule is:

```text
None   -> configured default
0      -> remains 0
False  -> remains False
other explicit value -> remains unchanged
```

`attrs.evolve()` is the immutable reconstruction mechanism; the `changes` mapping determines the defaulting policy.

Exact-type lookup is preferred initially:

```python
defaults.get(type(inp), {})
```

rather than inheritance-based matching.

---

## 18. Root configuration loading pipeline

The application-facing root class should expose one generic load operation:

```python
@classmethod
def load(
    cls,
    *,
    defaults: Defaults | None = None,
    normalizer: Callable[[Self], Self] | None = None,
    validator: Callable[[Self], None] | None = None,
) -> Self:
    ...
```

The processing order is:

```text
script response
      ↓
ConfigObject.from_mapping()
      ↓
apply_defaults()        optional
      ↓
normalizer(config)      optional
      ↓
validator(config)       optional
      ↓
immutable application snapshot
```

Conceptually:

```python
@classmethod
def load(
    cls,
    *,
    defaults=None,
    normalizer=None,
    validator=None,
) -> Self:
    response = load_one(cls.blueprint_path)
    config = cls.from_mapping(response)

    if defaults is not None:
        config = apply_defaults(config, defaults)

    if normalizer is not None:
        config = normalizer(config)

    if validator is not None:
        validator(config)

    return config
```

The validator should normally return `None` and raise an informative exception on failure rather than return an uninformative Boolean.

This class-level API means the application does not need to hand-write a schema-specific `get_app_config()` wrapper.

---

## 19. Normalization versus validation

Normalization and validation are separate application concerns.

### 19.1 Normalizer

A normalizer returns a new configuration snapshot in canonical form:

```python
Callable[[T], T]
```

Examples:

- merge overlapping schedule intervals;
- merge directly adjacent intervals when they represent continuous behavior;
- sort schedule entries into a canonical order;
- normalize labels or other redundant representations.

### 19.2 Validator

A validator checks invariants that remain after normalization:

```python
Callable[[T], None]
```

It raises an informative exception on failure.

Examples:

- impossible application combinations;
- duration beyond an application-specific limit;
- inconsistent semantic relationships that Home Assistant selectors cannot express.

These are application rules and should not become part of the generic generator schema language.

---

## 20. Configuration change detection

Editing a script created from a blueprint causes the script service to be re-registered. PyScript can observe Home Assistant's `service_registered` event.

A representative event payload is:

```python
{
    "event_type": "service_registered",
    "domain": "script",
    "service": "pyscript_solar_discharge_2",
    ...,
}
```

The event provides the service name, which corresponds to the script's immutable unique ID.

The framework can map:

```text
script service / unique_id
        ↓
entity registry
        ↓
current script entity_id
        ↓
blueprint_in_script(...)
        ↓
blueprint path
```

through a shared helper such as:

```python
blueprint_from_script_service(service_name)
```

This is the inverse of normal load discovery:

```text
load:
blueprint path -> entity_id -> unique_id/service

change detection:
unique_id/service -> entity_id -> blueprint path
```

---

## 21. Class-generated change trigger

PyScript decorators themselves are interpreted specially, so `blueprint-config` should not try to invent a new decorator that wraps `event_trigger`.

Instead, the configuration class can generate arguments for the existing decorator:

```python
@classmethod
def change_trigger(cls) -> tuple[str, str]:
    return (
        EVENT_SERVICE_REGISTERED,
        (
            "domain == 'script' and "
            "blueprint_from_script_service(service) == "
            f"{cls.blueprint_path!r}"
        ),
    )
```

Application code can then write:

```python
@event_trigger(*SolarDischargeConfig.change_trigger())
def on_config_change(**kwargs):
    ...
```

The trigger expression checks `domain == 'script'` first so the blueprint lookup is not performed for unrelated service registrations.

The registered-service edge is useful because the replacement script is available to call when the event is observed.

---

## 22. Application snapshot refresh

Generated modules should not require a predefined mutable module-level `CONFIG` object.

Instead, the application explicitly owns the current snapshot:

```python
CONFIG = SolarDischargeConfig.load(
    defaults=SOLAR_DEFAULTS,
    normalizer=normalize_schedule,
    validator=validate_schedule,
)
```

On configuration change:

```python
@event_trigger(*SolarDischargeConfig.change_trigger())
def on_config_change(**kwargs):
    global CONFIG

    CONFIG = SolarDischargeConfig.load(
        defaults=SOLAR_DEFAULTS,
        normalizer=normalize_schedule,
        validator=validate_schedule,
    )

    rebuild_runtime_state()
```

This avoids stale imported bindings that could occur if a generated module internally replaced a global `CONFIG` object after another module had executed:

```python
from some_config import CONFIG
```

The application explicitly controls when its snapshot is replaced and what additional state must be rebuilt after the change.

---

## 23. Validation philosophy

The framework should remain thin.

### 23.1 Home Assistant owns selector constraints

Do not duplicate ordinary selector constraints such as:

- number min/max;
- select choices;
- entity integration/domain filters;
- device filters; or
- normal selector field shapes.

### 23.2 Framework invariants

Checks that do belong to `blueprint-config` include:

- singleton/multiple-instance cardinality;
- response must be mapping-like;
- generated required fields must not be `None`;
- representation conversion must succeed;
- recursively expected shapes must match generated types; and
- stale/incompatible generated code should fail clearly.

### 23.3 Application invariants

Rules such as schedule interval overlap, control-specific allowable states, or cross-field relationships belong in normalizers/validators supplied by the application.

---

## 24. Initial selector-to-Python mapping

A conservative mapping is:

| Selector | Generated representation |
|---|---|
| `boolean` | `bool | None` unless guaranteed |
| `number` | `float | None` unless guaranteed |
| `text` | `str | None` unless guaranteed |
| `time` | `datetime.time | None`, via `to_time` |
| `duration` | `datetime.timedelta | None`, via `to_timedelta` |
| `date` | `datetime.date | None`, future converter |
| `datetime` | `datetime.datetime | None`, future converter |
| `entity` | `str | None`; collection when `multiple` |
| `device` | `str | None`; collection when `multiple` |
| `area` | `str | None`; collection when `multiple` |
| `select` | `str | None`; possibly `Literal[...]` later |
| `object` with `fields` | generated `ConfigObject` subclass |
| `object` with `multiple: true` | `tuple[GeneratedConfigObject, ...]` |
| nested `object` | recursively generated `ConfigObject` subclass; implementation to be proven |
| unknown selector | `Any` or explicit unsupported error; still open |

A field marked `required: true` may narrow the generated type to non-optional and use the shared `not_none` validator.

---

## 25. Vertical slice: light control

The light-control prototype established:

- repeated `object` selector values represented as `tuple[LightConfig, ...]`;
- optional fields represented by `None`;
- `required: true` as a non-`None` generated invariant;
- time conversion from Home Assistant strings to `datetime.time`;
- global defaults returned as normal blueprint inputs;
- explicit type-keyed application defaults; and
- recursive `apply_defaults()`.

A representative generated shape is:

```python
@frozen
class LightConfig(ConfigObject):
    light: str = field(validator=not_none)
    button: str | None = None
    brightness_high: float | None = None
    brightness_low: float | None = None
    bright_start: dt.time | None = field(default=None, converter=to_time)
    bright_end: dt.time | None = field(default=None, converter=to_time)


@frozen
class LightControlConfig(BlueprintConfig):
    blueprint_path = "pyscript/light_control.yaml"

    lights: tuple[LightConfig, ...]
    default_brightness_high: float
    default_brightness_low: float
    default_bright_start: dt.time = field(converter=to_time)
    default_bright_end: dt.time = field(converter=to_time)
```

The prototype showed that the Python representation can remain almost entirely declarative.

---

## 26. Vertical slice: solar discharge

The solar-discharge example is intentionally more demanding because it has application-level schedule semantics.

The current Home Assistant script instance stores data shaped like:

```yaml
pyscript_solar_discharge:
  alias: Pyscript Solar Discharge
  use_blueprint:
    path: pyscript/solar_discharge.yaml
    input:
      pw_op_mode: select.powerwall_operation_mode
      pw_export_mode: select.powerwall_allow_export
      schedule:
        - month: June
          label: Weekday 6-6:45 PM
          start_time: '18:00:00'
          duration:
            hours: 0
            minutes: 45
            seconds: 0
```

The useful abstraction is a **list of discharge windows**, not a fixed object per month.

That permits:

- zero schedule entries for a month;
- multiple entries for the same month;
- separate weekday/weekend entries;
- multiple windows in one day type; and
- unusual but legitimate policies such as discharging during every odd hour.

A representative generated model is:

```python
@frozen
class ScheduleConfig(ConfigObject):
    month: str
    label: str | None = None
    weekend: bool = False
    start_time: dt.time = field(converter=to_time)
    duration: dt.timedelta = field(converter=to_timedelta)


@frozen
class SolarDischargeConfig(BlueprintConfig):
    blueprint_path = "pyscript/solar_discharge.yaml"

    pw_op_mode: str
    pw_export_mode: str
    schedule: tuple[ScheduleConfig, ...]
```

### 26.1 Schedule normalization

For a given `(month, weekend)` partition, any number of windows may exist.

A solar-discharge normalizer may:

1. convert each entry to a time interval;
2. sort intervals by start time;
3. merge overlapping intervals;
4. optionally merge directly adjacent intervals; and
5. return a canonical configuration copy.

For example:

```text
18:00-19:00
18:30-19:30
```

normalizes to:

```text
18:00-19:30
```

Likewise:

```text
18:00-19:00
19:00-20:00
```

may normalize to:

```text
18:00-20:00
```

if the application treats touching intervals as continuous discharge.

Cross-midnight intervals must be handled deliberately rather than assuming all windows end on the same calendar day.

The generic framework does not know any of these rules; it merely provides the normalizer hook.

---

## 27. Concrete generated Python versus `.pyi`

The preferred MVP output is concrete typed Python source.

Because generated classes contain real annotations such as:

```python
@frozen
class ScheduleConfig(ConfigObject):
    start_time: dt.time
    duration: dt.timedelta
```

Pylance/Pyright can infer the API from the `.py` module directly.

A separate `.pyi` is therefore not required for the MVP.

A stub may become useful later if runtime classes are dynamically manufactured or if the public typing surface intentionally diverges from the runtime implementation.

---

## 28. Jupyter workflow

Jupyter remains an important design environment because it makes the actual configuration response and generated object behavior easy to inspect interactively.

Typical development usage should resemble production usage:

```python
from blueprint_config.solar_discharge import SolarDischargeConfig

CONFIG = SolarDischargeConfig.load(
    normalizer=normalize_schedule,
    validator=validate_schedule,
)
```

The notebook can inspect raw response values, generated types, normalized schedules, and change-trigger behavior before the generator is implemented.

If generated modules are rewritten while a Jupyter kernel is running, normal module caching may require `importlib.reload()` or a kernel restart.

---

## 29. Generation responsibilities

Generation should be a normal Python build/configuration step, not part of Home Assistant startup.

Possible CLI forms remain:

```bash
blueprint-config generate path/to/blueprint_config.yaml
```

or:

```bash
python -m blueprint_config generate path/to/blueprint_config.yaml
```

Likely generator responsibilities are now:

1. read the source YAML;
2. validate small framework metadata;
3. preserve/pass through native Home Assistant selector syntax;
4. derive configuration object structure from selectors;
5. recursively emit `ConfigObject` subclasses for structured fields;
6. emit one root `BlueprintConfig` subclass;
7. derive optional versus required annotations;
8. attach shared converters such as `to_time` and `to_timedelta`;
9. attach narrow framework validators such as `not_none` where appropriate;
10. generate the script response sequence if it is not already present;
11. generate configuration package `__init__.py` exports;
12. write/install the blueprint and generated Python package; and
13. report selector shapes it cannot yet type safely.

Notably, the generator should **not** need to emit a custom recursive `_from_response()` factory for every schema. The generated annotations plus `ConfigObject.from_mapping()` should carry that responsibility.

---

## 30. `#generated` staging

A source-local `#generated/` directory remains useful as build output/staging:

```text
scripts/solar_discharge/
    solar_discharge.py
    blueprint_config.yaml
    #generated/
        solar_discharge.yaml
        solar_discharge/
            __init__.py
            config.py
```

Possible uses include:

- inspecting generated output;
- Git diffs;
- staging deployment;
- keeping generated Python away from PyScript's recursive `scripts` loader; and
- debugging install contents.

Generated output is derived, not canonical source.

---

## 31. Distribution model

Distribution should normally ship source plus the configuration definition and rebuild on the recipient system.

This allows recipients to customize selectors for their integrations/devices and regenerate the corresponding blueprint/model rather than accepting a build made for another Home Assistant installation.

Generated files may be shipped for reference or convenience but should be considered derived and rebuildable.

---

## 32. Build versus deployment

The generator should separate **what files belong where** from **how they reach the Home Assistant system**.

When `/config` is locally available, live output can be written directly to locations such as:

```text
/config/blueprints/script/blueprint_config/...
/config/pyscript/modules/blueprint_config/...
```

When generation occurs elsewhere, the tool can create an install-shaped staging tree and let external mechanisms transport it:

- Samba mount;
- SSHFS;
- `scp`;
- `rsync`; or
- another filesystem synchronization mechanism.

The MVP should not own remote authentication or transport configuration.

---

## 33. Error reporting

Errors should be actionable and should eventually be surfaced through Home Assistant notifications as well as logs when user intervention is required.

Important cases include:

- malformed framework metadata;
- zero/multiple singleton instances according to final cardinality policy;
- missing entity-registry entry;
- script call failure;
- non-mapping response;
- required field missing or `None`;
- unsupported recursive/container type shape;
- converter failure;
- normalizer failure;
- validator failure; and
- stale/incompatible generated code versus returned response.

Application semantic errors should preserve the application's descriptive exception message rather than collapse into a generic `False` validation result.

---

## 34. Current prototype status

The runtime/design work has now demonstrated or established:

- a real script blueprint returning configuration data;
- discovery by blueprint path using `scripts_with_blueprint()`;
- service resolution through entity-registry `unique_id`;
- synchronous `return_response=True` retrieval;
- a generic `load_one()` adapter;
- configuration-specific importable subpackages;
- frozen attrs configuration objects;
- repeated object values represented as tuples;
- time conversion to `datetime.time`;
- duration conversion design to `datetime.timedelta`;
- recursive type-keyed defaults using `attrs.evolve()`;
- service-registration events as a practical configuration-change signal;
- service-name-to-blueprint reverse lookup;
- event-trigger argument generation via a configuration class method;
- explicit immutable configuration snapshot replacement;
- `ConfigObject` as the structural-construction base;
- `BlueprintConfig` as the root lifecycle ABC;
- generic `from_mapping()` as the replacement for generated bespoke response factories; and
- `load(defaults=..., normalizer=..., validator=...)` as the preferred application-facing retrieval API.

The remaining work is primarily to turn these proven output shapes into generator rules.

---

## 35. MVP implementation plan

1. Refactor the current shared runtime around `ConfigObject` and `BlueprintConfig`.
2. Make `BlueprintConfig` an ABC and enforce a blueprint path on concrete root classes.
3. Narrow `load_one()` to raw discovery/retrieval.
4. Implement generic recursive `ConfigObject.from_mapping()` for direct nested objects and `tuple[T, ...]`.
5. Move `to_time`, `to_timedelta`, and `not_none` into shared framework code.
6. Finish/test recursive `apply_defaults()` using `attrs.evolve()`.
7. Implement `BlueprintConfig.load(defaults, normalizer, validator)`.
8. Implement `blueprint_from_script_service()`.
9. Implement/test `BlueprintConfig.change_trigger()` with PyScript `event_trigger`.
10. Use `light_control` as the defaults/optionality regression example.
11. Use `solar_discharge` as the repeated-object, duration, refresh, and normalization example.
12. Add an explicit nested-object practical example before claiming full nested-selector support.
13. Define initial selector-to-Python type mapping from the working examples.
14. Generate concrete typed `config.py` source from those proven rules.
15. Generate/install the corresponding script blueprint.
16. Test the same API in Jupyter and normal PyScript.
17. Add cardinality notifications/error handling.
18. Add `instances: many` after singleton behavior is stable.
19. Add CLI/build/deployment mechanics after runtime generation is proven.
20. Revisit `.pyi` only if concrete generated Python proves insufficient.

---

## 36. Open design questions

### 36.1 Zero singleton instances

Should an exactly-one `BlueprintConfig.load()` return `None` when no matching script exists, or should zero instances always be a configuration error with a Home Assistant notification?

The current class API is cleaner if `load()` returns `Self`, which argues for treating zero as an error, but the earlier prototype used `None` to allow a consumer to terminate quietly.

### 36.2 Unknown selectors

When the generator encounters a selector it does not understand, should it:

- pass it through and type the value as `Any`; or
- fail generation with an explicit unsupported-selector error?

### 36.3 Multiple instances

For `instances: many`, should the API be a separate root class method such as `load_all()`, and should framework metadata such as source script entity IDs be exposed separately from the user configuration objects?

### 36.4 Nested object implementation boundary

The generic object model makes nested selectors feasible. How much recursive type/container machinery belongs in the MVP before another real configuration requires it?

### 36.5 Configuration-change edge cases

A `service_registered` event is useful for changed scripts, but runtime behavior should be tested for:

- script deletion;
- disabling/re-enabling a configuration script;
- Home Assistant script reloads where configuration did not materially change;
- rename behavior; and
- startup ordering relative to PyScript initialization.

### 36.6 Generated artifact manifest

Would a small manifest of generated files and target paths materially improve installation, cleanup, or deployment?

### 36.7 Normalizer return type

The preferred simple contract is `Callable[[T], T]`. If an application eventually needs normalization to produce a distinct operational type, that should be introduced deliberately rather than generalized prematurely.

---

## 37. Design principles

1. **Start from real Home Assistant UI/runtime examples and work backward to generator rules.**
2. **Use Home Assistant's configuration language where it already exists.**
3. **Keep framework metadata small.**
4. **Separate Home Assistant configuration, framework mechanics, and application policy.**
5. **Use immutable typed attrs objects at the application boundary.**
6. **Use generated annotations as executable structural metadata.**
7. **Centralize recursive construction in `ConfigObject.from_mapping()` instead of generating bespoke factories.**
8. **Use `BlueprintConfig` only for root objects that have blueprint lifecycle/identity.**
9. **Treat configuration instances as replaceable snapshots, not singletons.**
10. **Use converters for representation changes, not duplicate validation.**
11. **Use `required` only to strengthen the non-`None` runtime contract.**
12. **Apply defaults explicitly by type rather than naming convention.**
13. **Replace only `None`; never treat falsy values as missing.**
14. **Normalize before validating when canonicalization can remove benign inconsistencies.**
15. **Keep application semantic validation outside the generic framework.**
16. **Use existing PyScript decorators; generate decorator arguments rather than inventing wrapper decorators.**
17. **Never silently choose among ambiguous singleton instances.**
18. **Keep Home Assistant internal API dependencies behind narrow adapters.**
19. **Keep generation out of Home Assistant startup/runtime.**
20. **Prefer concrete generated Python before adding `.pyi` complexity.**
21. **Treat `#generated` as staging/build output, not canonical source.**
22. **Distribute source/configuration definitions and rebuild after selector customization.**
23. **Separate generation/install layout from transport/deployment mechanics.**
24. **Keep Jupyter and production APIs as similar as possible.**
25. **Prefer a small understandable framework over a comprehensive second configuration system.**

---

## 38. Recommended next step

Before writing the generator, implement the new generic runtime object model by hand and make both current examples use it.

The target application usage should be approximately:

```python
from blueprint_config.solar_discharge import SolarDischargeConfig

CONFIG = SolarDischargeConfig.load(
    defaults=SOLAR_DEFAULTS,
    normalizer=normalize_schedule,
    validator=validate_schedule,
)


@event_trigger(*SolarDischargeConfig.change_trigger())
def on_config_change(**kwargs):
    global CONFIG

    CONFIG = SolarDischargeConfig.load(
        defaults=SOLAR_DEFAULTS,
        normalizer=normalize_schedule,
        validator=validate_schedule,
    )

    rebuild_runtime_state()
```

and the generated configuration module should need little more than declarative attrs classes:

```python
@frozen
class ScheduleConfig(ConfigObject):
    month: str
    label: str | None = None
    weekend: bool = False
    start_time: dt.time = field(converter=to_time)
    duration: dt.timedelta = field(converter=to_timedelta)


@frozen
class SolarDischargeConfig(BlueprintConfig):
    blueprint_path = "pyscript/solar_discharge.yaml"

    pw_op_mode: str
    pw_export_mode: str
    schedule: tuple[ScheduleConfig, ...]
```

Once this works without schema-specific loading code, the generator has a sharply defined task: **emit the classes and blueprint plumbing that the proven runtime already knows how to consume.**
