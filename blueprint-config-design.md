# `pyscript-bp-config` Design

**Status:** Draft  
**Design version:** 0.3  
**Last revised:** 2026-08-12  
**Canonical format:** Markdown

## 1. Summary

`pyscript-bp-config` provides GUI-backed, typed configuration for Home Assistant PyScript applications by using **script blueprints as configuration instances**.

A compact YAML schema describes:

- framework metadata under `pyscript:`;
- the blueprint display name and description; and
- configuration fields using Home Assistant's native blueprint `input:` and selector syntax.

From that one schema, a generator produces:

1. a Home Assistant **script blueprint** that collects configuration values and returns them as script response data;
2. an importable PyScript **runtime module** that discovers scripts based on that blueprint and converts their returned values into immutable `attrs` objects; and
3. a matching **`.pyi` type stub** for Pylance/Pyright and other type-aware tooling.

The application then consumes configuration through ordinary Python attributes:

```python
from bpconfig.powerwall_export import CONFIG

if CONFIG.enabled and battery_soc > CONFIG.min_soc:
    ...
```

For a configuration type that supports multiple instances:

```python
from bpconfig.room_control import CONFIGS

for config in CONFIGS:
    control_room(config)
```

Home Assistant owns selector-value validation. The framework validates only its own metadata and runtime structural contract, enforces the requested number of configuration instances, and performs lightweight representation conversion where useful.

---

## 2. Goals

The framework should:

- expose PyScript application configuration through Home Assistant's existing GUI;
- use Home Assistant's own blueprint input/selector syntax instead of inventing a parallel field DSL;
- support typed attribute access such as `CONFIG.min_soc` and `CONFIG.export.start`;
- support nested structured data through selectors that actually return mappings, especially the object selector;
- support both exactly-one and multiple configuration instances;
- make every schema file self-contained so generation requires no extra metadata arguments;
- generate blueprint YAML, runtime loading code, and `.pyi` typing information from one source of truth;
- work naturally from both normal PyScript files and the PyScript Jupyter environment;
- rely on Home Assistant for selector parsing and validation wherever practical; and
- keep dependence on Home Assistant Python internals narrow and isolated.

## 3. Non-goals

The framework is not intended to:

- replace Home Assistant config entries;
- become a general-purpose Home Assistant integration framework;
- duplicate Home Assistant's selector validation in `attrs`, Voluptuous, or framework-specific validators;
- manage secrets;
- require code generation on every Home Assistant startup; or
- infer arbitrary Python models from unrelated YAML.

---

## 4. Terminology

**Schema**  
The source YAML file consumed by `pyscript-bp-config`.

**Generated blueprint**  
A Home Assistant script blueprint generated from the schema.

**Configuration instance**  
A Home Assistant script created from the generated blueprint. Each such script stores one set of user-selected configuration values.

**Runtime adapter**  
Generated/importable Python code that discovers configuration instances, calls them, converts their responses, and exports `CONFIG` or `CONFIGS`.

**Configuration model**  
The immutable nested `attrs` object exposed to PyScript application code.

---

## 5. Canonical schema format

The schema intentionally resembles the `blueprint:` metadata of a Home Assistant blueprint. The only framework-specific portion is the top-level `pyscript:` block.

```yaml
pyscript:
  module: powerwall_export
  instances: one

name: Powerwall Export
description: >
  Configuration for scheduled Powerwall export behavior.

input:
  enabled:
    name: Enabled
    description: Allow scheduled export.
    default: true
    selector:
      boolean:

  min_soc:
    name: Minimum SOC
    description: Lowest battery state of charge allowed during export.
    default: 40
    selector:
      number:
        min: 0
        max: 100
        unit_of_measurement: "%"

  export:
    name: Export settings
    description: Export window and power limit.
    selector:
      object:
        fields:
          start:
            label: Start time
            description: Earliest time export may begin.
            selector:
              time:

          end:
            label: End time
            description: Time export must stop.
            selector:
              time:

          max_power:
            label: Maximum power
            selector:
              number:
                min: 0
                max: 10000
```

### 5.1 Framework metadata

Initial metadata should remain deliberately small:

```yaml
pyscript:
  module: powerwall_export
  instances: one
```

#### `module`

Required. A stable Python-style identifier used to derive generated artifact names and configuration class names.

For example:

```text
module: powerwall_export

blueprint path:  pyscript/powerwall_export.yaml
runtime module:  bpconfig/powerwall_export.py
stub:            bpconfig/powerwall_export.pyi
model class:     PowerwallExportConfig
```

The module identifier, not the human-readable blueprint name, is the stable identity of the configuration type.

#### `instances`

Required. Initial values:

```yaml
instances: one
```

or:

```yaml
instances: many
```

`one` causes the runtime adapter to export:

```python
CONFIG: PowerwallExportConfig
```

`many` causes it to export:

```python
CONFIGS: list[PowerwallExportConfig]
```

A future version could generalize cardinality if a real use case appears, but the first design should not add unused `minimum`, `maximum`, or similar options.

### 5.2 Blueprint name and description

`name` is required and remains outside `pyscript:` because it is native blueprint metadata:

```yaml
name: Powerwall Export
```

`description` is optional but strongly recommended:

```yaml
description: >
  Configuration for scheduled Powerwall export behavior.
```

Input and section descriptions should likewise be preserved as native Home Assistant metadata. They provide useful GUI documentation essentially for free and may later be reused in generated documentation.

### 5.3 No separate Python selector DSL

The framework should **not** introduce constructs such as:

```python
Number(...)
Boolean(...)
Entity(...)
Group(...)
```

Home Assistant's selector syntax is already the schema language. This avoids maintaining a second representation of every selector and reduces the amount of framework code that must track Home Assistant changes.

---

## 6. Input sections versus nested data

Home Assistant blueprint input sections are **UI grouping only**. Inputs inside a section still have globally unique names and are referenced directly by those names.

Therefore this:

```yaml
input:
  export_settings:
    name: Export settings
    input:
      start:
        selector:
          time:
      end:
        selector:
          time:
```

must not imply that Home Assistant returns:

```python
{"export_settings": {"start": ..., "end": ...}}
```

The framework should preserve Home Assistant semantics rather than reinterpret visual sections as data nesting.

Actual nested configuration should come from selectors whose **value is actually structured**, especially an object selector:

```yaml
input:
  export:
    selector:
      object:
        fields:
          start:
            selector:
              time:
          end:
            selector:
              time:
```

That value naturally maps to:

```python
CONFIG.export.start
CONFIG.export.end
```

An object selector with `multiple: true` can naturally map to a typed collection of nested model objects.

---

## 7. Home Assistant as schema parser

The framework should avoid implementing its own blueprint parser.

### 7.1 Validate the synthesized blueprint

The generator should construct the complete blueprint structure and pass it through Home Assistant's blueprint schema:

```python
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA

blueprint_data = {
    "blueprint": {
        "name": schema["name"],
        "description": schema.get("description"),
        "domain": "script",
        "input": schema.get("input", {}),
    },
    "sequence": generated_sequence,
}

validated = BLUEPRINT_SCHEMA(blueprint_data)
```

This delegates blueprint metadata, input-section, selector declaration, and duplicate-input-name validation to Home Assistant.

The narrower `BLUEPRINT_INPUT_SCHEMA` and `BLUEPRINT_INPUT_SECTION_SCHEMA` currently exist in Home Assistant Core, but the framework should prefer the full `BLUEPRINT_SCHEMA` so it depends on fewer implementation-level objects.

### 7.2 Preserve the input tree

Home Assistant exposes helpers that flatten sectioned inputs for blueprint processing. That flattened representation is useful for resolving `!input` references, but it loses section structure.

The generator should therefore retain the validated/original `blueprint.input` tree when it needs layout or documentation information.

### 7.3 Use selector helpers for type analysis

Selector declarations can be interpreted using Home Assistant's selector helper:

```python
from homeassistant.helpers import selector

sel = selector.selector(input_definition["selector"])
```

The framework uses the resulting selector object/configuration only to infer:

- a Python static type;
- whether a value is scalar or multiple;
- whether recursive object handling is needed; and
- whether a representation conversion is desirable.

It should not build a second validator from this information.

---

## 8. Generated artifacts

Given:

```text
schemas/powerwall_export.yaml
```

the generator should derive all outputs from the schema metadata:

```text
schemas/powerwall_export.yaml
        |
        +--> <config>/blueprints/script/pyscript/powerwall_export.yaml
        |
        +--> <config>/pyscript/modules/bpconfig/powerwall_export.py
        |
        +--> <config>/pyscript/modules/bpconfig/powerwall_export.pyi
```

The exact root paths may be configurable globally, but no per-schema naming arguments should be required.

### 8.1 Generated script blueprint

The generated blueprint contains no application behavior. Its only job is to collect the selected inputs and return them as a mapping.

Conceptually:

```yaml
blueprint:
  name: Powerwall Export
  description: Configuration for scheduled Powerwall export behavior.
  domain: script
  input:
    # copied from schema
    ...

sequence:
  - variables:
      config:
        enabled: !input enabled
        min_soc: !input min_soc
        export: !input export

  - stop: Return PyScript configuration
    response_variable: config
```

Home Assistant requires returned script response data to be a mapping. That is a good fit for the configuration boundary.

---

## 9. Runtime discovery

The runtime adapter discovers configuration scripts by the generated blueprint path, not by script entity naming convention.

Home Assistant Core currently provides:

```python
from homeassistant.components.script import scripts_with_blueprint

entity_ids = scripts_with_blueprint(
    hass,
    "pyscript/powerwall_export.yaml",
)
```

It also provides the inverse helper:

```python
from homeassistant.components.script import blueprint_in_script
```

All dependence on these Home Assistant Core helpers should live behind one small framework adapter.

### 9.1 `hass` access

Using `scripts_with_blueprint` from PyScript requires access to the Home Assistant `hass` object. PyScript provides this when `hass_is_global` is enabled.

The framework should document this as a prerequisite.

---

## 10. Instance cardinality

### 10.1 `instances: one`

Exactly one usable script instance must exist for the generated blueprint.

```text
number of discovered usable instances

0    -> configuration error + notification
1    -> load CONFIG
>1   -> configuration error + notification
```

The framework must never choose an arbitrary instance when more than one exists.

The diagnostic should identify:

- the configuration/blueprint name;
- the expected cardinality;
- the number found; and
- discovered entity IDs when helpful.

Example message:

```text
PyScript configuration error: Powerwall Export requires exactly one
configuration script, but 2 were found:
script.powerwall_export and script.powerwall_export_test.
```

A cardinality error should also be logged. The application should not receive a fabricated default `CONFIG` object.

### 10.2 `instances: many`

Zero or more usable instances are valid initially:

```python
CONFIGS: list[RoomControlConfig]
```

Each discovered script is called independently and converted into one configuration model object.

For the MVP, the source script entity ID should be kept as framework metadata rather than inserted into the user-defined configuration schema. Possible representations include:

```python
ConfigInstance(entity_id="script.kitchen", config=...)
```

or a private/generated metadata attribute. This remains an open API choice.

### 10.3 Usable-instance semantics

`script_with_blueprint()` operates on loaded script entities. The discovery adapter should additionally reject unavailable/non-callable instances if necessary and should define "usable" in one place.

The rest of the framework should not know how Home Assistant represents disabled or unavailable script entities.

---

## 11. Configuration retrieval

Each discovered configuration script is called synchronously and its response is returned directly to PyScript.

PyScript supports service response data using `return_response=True`:

```python
response = service.call(
    "script",
    service_name,
    return_response=True,
)
```

or through the equivalent virtual service call when the name is static.

This replaces the earlier event-based idea.

### 11.1 Why script responses are preferable to events

A direct response avoids:

- a custom event listener;
- correlation/request IDs;
- race handling;
- timeout bookkeeping; and
- unrelated listeners seeing configuration-return events.

The generated script behaves much more like a configuration function:

```text
PyScript ---- call ----> generated configuration script
         <--- dict -----
```

---

## 12. Validation philosophy

### 12.1 Home Assistant owns value validation

Selector definitions already describe what values Home Assistant will accept and provide the GUI used to enter those values.

The framework should **not** duplicate constraints such as:

```text
number min/max
select choices
entity-selector syntax
boolean type
object field shape
```

in `attrs` or in a parallel Voluptuous schema.

This is a deliberate design principle:

> Home Assistant validates configuration values. `pyscript-bp-config` validates its framework contract and converts already-valid values into convenient Python representations.

### 12.2 What the framework still validates

The framework should check only things that Home Assistant cannot own for it:

- `pyscript:` metadata syntax;
- the required `module` and `instances` values;
- generated artifact naming constraints;
- expected configuration-instance cardinality;
- that a service response is a mapping;
- that fields required by the generated model are present;
- that recursive conversion succeeds; and
- compatibility/version mismatches between schema, generated files, and loaded configuration.

### 12.3 Cross-field semantic rules

Some application semantics cannot be expressed by independent selectors, for example:

```text
start < end
minimum_soc < target_soc
```

Those should initially remain normal application checks rather than motivating a general framework validation language.

---

## 13. Runtime model with `attrs`

`attrs` is used primarily as an immutable structured container, not as a second validation system.

Conceptually:

```python
from attrs import frozen
import datetime as dt


@frozen
class ExportConfig:
    start: dt.time
    end: dt.time
    max_power: float


@frozen
class PowerwallExportConfig:
    enabled: bool
    min_soc: float
    export: ExportConfig
```

Application code gets natural attribute access:

```python
CONFIG.min_soc
CONFIG.export.start
CONFIG.export.max_power
```

The implementation may construct these classes dynamically rather than emitting concrete Python class source.

### 13.1 Conversion versus validation

Converters are appropriate when the desired Python representation differs from Home Assistant's selector result.

For example, a Home Assistant time selector value can be converted from its string representation into:

```python
datetime.time
```

This is representation conversion, not revalidation of the selector's constraints.

### 13.2 Initial selector/type mapping

The first implementation can support a conservative mapping such as:

| Selector | Runtime/static representation |
|---|---|
| `boolean` | `bool` |
| `number` | `float` (or a more specific numeric type when safely inferable) |
| `text` | `str` |
| `time` | `datetime.time` after conversion |
| `date` | `datetime.date` after conversion |
| `datetime` | `datetime.datetime` after conversion |
| `entity` | `str`; collection when `multiple` |
| `device` | `str`; collection when `multiple` |
| `area` | `str`; collection when `multiple` |
| `select` | `str`, optionally `Literal[...]` for fixed choices |
| `object` with `fields` | generated nested `attrs` model |
| object with `multiple: true` | collection of generated nested models |
| unknown/pass-through selector | `Any`, unless unsupported semantics require an error |

The exact mapping should be derived from current Home Assistant selector behavior and covered by tests.

---

## 14. Generated runtime module and `.pyi`

Generated runtime code and its type stub should have the same basename and live together in an importable PyScript module package:

```text
<config>/pyscript/modules/bpconfig/
    __init__.py
    powerwall_export.py
    powerwall_export.pyi
```

This fits PyScript's normal shared-module mechanism and allows type-aware editors to treat the `.pyi` as the module's static interface while runtime Python executes the `.py` implementation.

### 14.1 Singleton stub

```python
import datetime as dt


class ExportConfig:
    start: dt.time
    end: dt.time
    max_power: float


class PowerwallExportConfig:
    enabled: bool
    min_soc: float
    export: ExportConfig


CONFIG: PowerwallExportConfig
```

### 14.2 Multiple-instance stub

```python
class RoomControlConfig:
    ...


CONFIGS: list[RoomControlConfig]
```

### 14.3 Why generate the stub separately

The runtime model may be constructed dynamically with `attrs`, but a language server cannot infer the resulting attributes reliably from that runtime metaprogramming.

The generated `.pyi` gives Pylance/Pyright explicit knowledge of:

```python
CONFIG.min_soc
CONFIG.export.start
```

and allows it to flag:

```python
CONFIG.export.does_not_exist
```

without requiring generated concrete implementation classes.

---

## 15. Jupyter workflow

The notebook and production PyScript code should use the **same import**:

```python
from bpconfig.powerwall_export import CONFIG
```

or:

```python
from bpconfig.room_control import CONFIGS
```

This avoids notebook-only typing declarations.

When generation occurs while the same Jupyter kernel remains active, runtime code may need to be reloaded:

```python
import importlib
import bpconfig.powerwall_export as cfg

importlib.reload(cfg)
CONFIG = cfg.CONFIG
```

Pylance/Pyright may also need to notice the rewritten `.pyi`; that is an editor refresh issue, not a runtime design problem.

Ruff can lint/format Python, stub, and notebook source, but the `.pyi` exists primarily for static type tooling such as Pylance/Pyright.

---

## 16. Package and repository naming

Use:

```text
Distribution / repository: pyscript-bp-config
Python package:            pyscript_bp_config
CLI command:               pyscript-bp-config
Generated import package:  bpconfig
```

The shorter `bp` abbreviation is acceptable in this context because `pyscript` already establishes the Home Assistant/PyScript domain.

The generated package name `bpconfig` is intentionally short because it appears frequently in application imports:

```python
from bpconfig.powerwall_export import CONFIG
```

---

## 17. Generator behavior

The generator should be able to accept either a schema file or a directory of schemas. Each schema is self-contained.

For each schema:

1. Load YAML.
2. Validate the small `pyscript:` metadata contract.
3. Derive artifact names from `pyscript.module`.
4. Build a complete script-blueprint structure.
5. Pass that structure through Home Assistant's `BLUEPRINT_SCHEMA`.
6. Preserve the validated/original `input` tree for layout/documentation analysis.
7. Walk selectors only far enough to derive Python types and conversions.
8. Generate the script sequence that returns all blueprint input values as one mapping.
9. Write the generated blueprint.
10. Generate the runtime adapter.
11. Generate the matching `.pyi` stub.
12. Optionally run format/lint checks on generated Python/stub files.
13. Report generated paths and any selector shapes that required `Any` or were unsupported.

No additional per-schema command-line options should be required.

---

## 18. Lifecycle and refresh

The MVP can use a simple lifecycle:

- generation occurs during development/deployment;
- configuration instances are created/edited through the Home Assistant UI;
- PyScript loads configuration during module/application initialization; and
- after configuration edits, a PyScript/script reload refreshes the configuration.

Automatic configuration-change watching can be added later if it provides meaningful ergonomic benefit.

Configuration model objects should be replaced on refresh rather than mutated.

---

## 19. Error reporting

The framework should make configuration failures conspicuous and actionable.

Errors should be both logged and, for conditions that require user action, surfaced through a Home Assistant notification or repair-style mechanism where practical.

Initial errors include:

- malformed framework metadata;
- generated blueprint rejected by Home Assistant's blueprint schema;
- zero instances when `instances: one`;
- multiple instances when `instances: one`;
- configuration script unavailable or not callable;
- missing/non-mapping script response;
- stale generated model versus returned structure; and
- conversion failure.

Messages should use the human-readable blueprint name, while internal lookup continues to use the stable module-derived blueprint path.

---

## 20. Trust and security boundary

The generated script blueprint is framework-owned infrastructure. Its sequence should be generated and should simply expose blueprint inputs as a script response.

Because values arrive through Home Assistant's blueprint/selector system, the runtime model can normally trust their selector-level validity.

The framework still checks structural consistency so a stale, manually modified, or incompatible generated artifact fails clearly.

Secrets should remain outside this mechanism. A blueprint-created script is convenient configuration storage, not a secret-management system.

---

## 21. Compatibility boundary

The design intentionally distinguishes stable-ish public behavior from Home Assistant Python implementation details.

The most sensitive dependency is runtime blueprint-instance discovery through:

```python
homeassistant.components.script.scripts_with_blueprint
```

That usage should be isolated in one adapter module.

Similarly, direct use of:

```python
homeassistant.components.blueprint.schemas.BLUEPRINT_SCHEMA
```

and selector internals should remain confined to the generator/schema-analysis layer.

If Home Assistant changes those Python APIs, the application-facing API (`CONFIG`, `CONFIGS`, generated models) should not need to change.

---

## 22. End-to-end example

### 22.1 Schema

```yaml
pyscript:
  module: room_control
  instances: many

name: Room Control
description: Configuration for one independently controlled room.

input:
  temperature_sensor:
    name: Temperature sensor
    selector:
      entity:
        filter:
          domain: sensor

  setpoint:
    name: Setpoint
    default: 70
    selector:
      number:
        min: 55
        max: 80
        unit_of_measurement: °F
```

### 22.2 Generation

```text
room_control.yaml
      |
      +--> blueprints/script/pyscript/room_control.yaml
      +--> pyscript/modules/bpconfig/room_control.py
      +--> pyscript/modules/bpconfig/room_control.pyi
```

### 22.3 Home Assistant UI

The user creates any number of scripts from the generated **Room Control** blueprint. Each script represents one room and is edited using Home Assistant's normal entity and number selectors.

### 22.4 PyScript runtime

```python
from bpconfig.room_control import CONFIGS

for config in CONFIGS:
    temperature = state.get(config.temperature_sensor)
    control_room(temperature, config.setpoint)
```

### 22.5 Static typing

The generated stub tells Pylance/Pyright that:

```python
CONFIGS: list[RoomControlConfig]
```

and that each item has typed `temperature_sensor` and `setpoint` attributes.

---

## 23. MVP implementation plan

1. Implement schema metadata parsing for `module` and `instances`.
2. Build a complete Home Assistant script blueprint from the source schema.
3. Validate it with `BLUEPRINT_SCHEMA`.
4. Generate a script response mapping from every non-section input.
5. Implement discovery through a small `scripts_with_blueprint()` adapter.
6. Implement `instances: one` and `instances: many` cardinality behavior.
7. Call configuration scripts with `return_response=True`.
8. Implement basic selector/type analysis.
9. Implement frozen dynamic `attrs` models.
10. Generate side-by-side `.pyi` stubs.
11. Add Home Assistant diagnostics for singleton-cardinality failures.
12. Verify the same generated import from both Jupyter and a normal PyScript file.

### 23.1 Suggested first test schema

The first proof of concept should include:

- one boolean;
- one numeric input;
- one entity selector;
- one time selector;
- one object selector with two or three fields; and
- both `instances: one` and `instances: many` test variants.

Test singleton discovery with zero, one, and two configuration scripts before expanding selector coverage.

---

## 24. Open design questions

### 24.1 Identity for multiple instances

Should the source script entity ID be exposed as:

```python
config.entity_id
```

kept outside the user model:

```python
ConfigInstance(entity_id=..., config=...)
```

or omitted unless explicitly requested?

### 24.2 Collection type

Should `CONFIGS` be a `list[...]` to match the stated API, or a `tuple[...]` to make the top-level collection immutable as well?

### 24.3 Optional inputs

How should an omitted optional input appear in the generated model and stub? Likely approaches include:

```python
str | None
```

or omission only when Home Assistant's script expansion makes that possible. This should be determined from actual blueprint behavior rather than guessed.

### 24.4 Unknown selectors

When Home Assistant adds a selector the generator does not yet understand, should generation:

- pass it through and type it as `Any`; or
- fail with an explicit unsupported-selector error?

A pass-through `Any` fallback would preserve forward compatibility, while a strict mode could be offered for users who prefer complete typing.

### 24.5 Schema/generated-artifact versioning

Should generated artifacts carry a small framework/schema version marker so stale runtime files can be detected deterministically?

### 24.6 Refresh semantics

Is explicit reload-after-edit sufficient, or should the runtime eventually react automatically when relevant script configurations are reloaded?

---

## 25. Design principles

The design should remain guided by these principles:

1. **Use Home Assistant's language where Home Assistant already has one.**
2. **Keep framework metadata minimal and self-contained.**
3. **Let Home Assistant validate selector values.**
4. **Do not reinterpret UI-only input sections as nested data.**
5. **Use actual structured selector values for nested Python models.**
6. **Use one stable module identifier for generated artifact identity.**
7. **Never silently choose among ambiguous singleton instances.**
8. **Keep runtime objects immutable and pleasant to use.**
9. **Generate typing information rather than requiring handwritten stubs.**
10. **Keep Home Assistant internal API dependencies behind narrow adapters.**
11. **Make Jupyter and production imports identical.**
12. **Prefer a small framework over a comprehensive duplicate of Home Assistant.**

---

## 26. Current platform references

The design was checked against the following current sources on 2026-08-12:

- [Home Assistant blueprint schema](https://www.home-assistant.io/docs/blueprint/schema/) — blueprint metadata, inputs, descriptions, and input sections.
- [Home Assistant selectors](https://www.home-assistant.io/docs/blueprint/selectors/) — selector behavior, including structured object selectors.
- [Home Assistant script syntax](https://www.home-assistant.io/docs/scripts/) — returning mapping response data with `stop` / `response_variable`.
- [Home Assistant Core blueprint schemas](https://github.com/home-assistant/core/blob/dev/homeassistant/components/blueprint/schemas.py) — `BLUEPRINT_SCHEMA`, input schemas, selector validation, and unique input validation.
- [Home Assistant Core script component](https://github.com/home-assistant/core/blob/dev/homeassistant/components/script/__init__.py) — `scripts_with_blueprint()`, `blueprint_in_script()`, and script response propagation.
- [Home Assistant Core selector helpers](https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/selector.py) — selector parsing/configuration classes used for type analysis.
- [PyScript reference](https://hacs-pyscript.readthedocs.io/en/latest/reference.html) — service response calls, `hass_is_global`, shared modules, and Jupyter/global-context behavior.

---

## 27. Recommended next step

Build the smallest vertical proof of concept rather than a broad selector framework:

```text
one schema YAML
    -> one validated generated script blueprint
    -> one generated runtime module
    -> one generated .pyi
    -> CONFIG available in Jupyter and normal PyScript
```

Then validate `instances: one` error handling and `instances: many`, followed by object-selector nesting. Once that works cleanly, additional selector typing should be mostly incremental.
