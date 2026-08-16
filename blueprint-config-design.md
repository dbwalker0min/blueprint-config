# `blueprint-config` Design

**Status:** Draft  
**Design version:** 0.4  
**Last revised:** 2026-08-13  
**Canonical format:** Markdown

## 1. Summary

`blueprint-config` provides GUI-backed, typed configuration for Home Assistant PyScript logic by using **script blueprints as configuration instances**.

A compact YAML definition lives beside the PyScript source and contains:

- framework metadata under `pyscript:`;
- the blueprint display name and description; and
- configuration fields expressed directly with Home Assistant's native blueprint `input:` and selector syntax.

From that one source definition, a developer-time generator produces:

1. a Home Assistant **script blueprint** that collects the selected values and returns them as script response data;
2. an importable PyScript **runtime module** that discovers script instances based on that blueprint and converts their responses into immutable `attrs` objects; and
3. a matching **`.pyi` type stub** for Pylance/Pyright and other type-aware tooling.

The generated artifacts can also be staged under a co-located `#generated/` directory for packaging and redistribution. Those staged files are build products; end users of a distributed package should not need to run the generator.

Home Assistant owns selector-value validation. The framework validates only its own metadata and runtime contract, enforces the requested instance cardinality, and performs lightweight representation conversion where useful.

---

## 2. Goals

The framework should:

- expose PyScript configuration through Home Assistant's existing GUI;
- use Home Assistant's own blueprint input/selector syntax rather than inventing a parallel field DSL;
- support typed attribute access such as `CONFIG.min_soc` and `CONFIG.export.start`;
- support actual nested structured values, especially through the object selector;
- support both exactly-one and multiple configuration instances;
- make every definition file self-contained so generation requires no extra per-schema arguments;
- generate blueprint YAML, runtime loading code, and `.pyi` typing information from one source of truth;
- work with top-level PyScript files, files under `pyscript/scripts`, or PyScript apps without requiring any one layout;
- work naturally from Jupyter during development;
- keep generated runtime modules in PyScript's supported `modules` tree;
- keep the schema definition physically beside the source logic when desired;
- support distributable packages that contain all generated artifacts and therefore require no generation on the recipient system;
- rely on Home Assistant for selector-value validation; and
- keep dependence on Home Assistant Python internals narrow and isolated.

## 3. Non-goals

The framework is not intended to:

- replace Home Assistant config entries;
- require the consumer to be a PyScript App;
- turn arbitrary directories under `pyscript/scripts` into Python packages;
- duplicate Home Assistant selector validation in `attrs`, Voluptuous, or framework-specific validators;
- manage secrets;
- require generation on Home Assistant startup;
- require generation during package installation; or
- infer arbitrary Python models from unrelated YAML.

---

## 4. Terminology

**Definition file**  
The canonical source YAML file, normally named `blueprint_config.yaml`, consumed by `blueprint-config`.

**Generated blueprint**  
A Home Assistant script blueprint generated from the definition file.

**Configuration instance**  
A Home Assistant script created from the generated blueprint. Each such script stores one set of user-selected configuration values.

**Runtime adapter**  
Generated/importable Python code that discovers configuration instances, calls them, converts their responses, and exports `CONFIG` or `CONFIGS`.

**Configuration model**  
The immutable nested `attrs` object exposed to PyScript application code.

**Consumer**  
The PyScript logic that imports and uses `CONFIG` or `CONFIGS`. A consumer may be a top-level PyScript file, a file below `scripts/`, or an App.

**Staged artifact**  
A generated file stored under the source unit's `#generated/` directory for inspection, version control, packaging, or redistribution.

**Installed artifact**  
The copy of a generated file placed in the Home Assistant path from which it is actually consumed.

---

## 5. Naming

Use the shorter, unambiguous names:

```text
Distribution / repository: blueprint-config
Python package:            blueprint_config
CLI command:               blueprint-config
PyScript framework module: blueprint_config
```

The framework's live PyScript package normally resides at:

```text
<config>/pyscript/modules/blueprint_config/
```

Generated runtime adapters can live under:

```text
<config>/pyscript/modules/blueprint_config/generated/
```

A normal consumer import is therefore:

```python
from blueprint_config.generated.powerwall_export import CONFIG
```

or, for a multiple-instance configuration:

```python
from blueprint_config.generated.room_control import CONFIGS
```

---

## 6. Recommended source layout

The framework must not require a PyScript App. A convenient layout for a logical unit is:

```text
<config>/pyscript/
└── scripts/
    └── powerwall_export/
        ├── powerwall_export.py
        ├── blueprint_config.yaml
        └── #generated/
            ├── powerwall_export.yaml
            ├── powerwall_export.py
            └── powerwall_export.pyi
```

PyScript recursively autoloads `.py` files below `pyscript/scripts`, but skips directories whose names begin with `#`. Therefore `#generated/` is a useful package-staging location: it can contain generated `.py` files without causing them to be autoloaded as independent PyScript global contexts.

The actual importable runtime copies live elsewhere:

```text
<config>/pyscript/modules/
└── blueprint_config/
    ├── __init__.py
    └── generated/
        ├── __init__.py
        ├── powerwall_export.py
        └── powerwall_export.pyi
```

The actual Home Assistant blueprint copy lives at:

```text
<config>/blueprints/script/blueprint_config/powerwall_export.yaml
```

### 6.1 Why not make the source directory a Python package?

Directories under `pyscript/scripts` are organizational only. Their `.py` files are recursively autoloaded as independent PyScript global contexts; an `__init__.py` there does not turn the directory into an ordinary importable package.

Importable PyScript modules belong under `pyscript/modules`, while package-form PyScript Apps belong under `pyscript/apps`.

The framework therefore uses `scripts/<unit>/` for source organization and `modules/blueprint_config/generated/` for generated importable runtime code.

### 6.2 The `#` trick is optional

A leading-`#` directory is useful when generated or development-only `.py` files must sit beside PyScript source. It should remain an optional organizational mechanism, not a runtime requirement.

If a developer ever needs to import ordinary native Python from such an ignored directory, the directory can be placed on `PYTHONPATH`/`sys.path` in an appropriate native-Python environment. That is an escape hatch rather than the normal framework design.

---

## 7. Canonical definition format

The definition intentionally resembles the metadata and `input:` portion of a Home Assistant blueprint. The only framework-specific portion is the top-level `pyscript:` block.

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

### 7.1 Framework metadata

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

installed blueprint: blueprints/script/blueprint_config/powerwall_export.yaml
runtime module:      blueprint_config/generated/powerwall_export.py
stub:                blueprint_config/generated/powerwall_export.pyi
model class:         PowerwallExportConfig
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
CONFIGS: tuple[PowerwallExportConfig, ...]
```

A future version can generalize cardinality if a real use case appears.

### 7.2 Blueprint name and description

`name` is required and remains outside `pyscript:` because it is native blueprint metadata:

```yaml
name: Powerwall Export
```

`description` is optional but strongly recommended:

```yaml
description: >
  Configuration for scheduled Powerwall export behavior.
```

Input, section, and object-field descriptions should likewise be preserved as native Home Assistant metadata. They provide useful GUI documentation essentially for free.

### 7.3 No separate Python selector DSL

The framework should **not** introduce parallel constructs such as:

```python
Number(...)
Boolean(...)
Entity(...)
Group(...)
```

Home Assistant's selector syntax is already the schema language.

---

## 8. Input sections versus nested data

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

An object selector with `multiple: true` can naturally map to a typed immutable collection of nested model objects.

---

## 9. Parsing and Home Assistant validation

The framework should avoid becoming a second implementation of Home Assistant's blueprint parser.

### 9.1 Generator should remain usable as a normal Python CLI

Generation is a developer/build-time activity and should be invokable from a shell or Jupyter terminal:

```bash
blueprint-config generate \
    /config/pyscript/scripts/powerwall_export/blueprint_config.yaml
```

or recursively:

```bash
blueprint-config generate /config/pyscript/scripts
```

The recursive form should discover `blueprint_config.yaml` files automatically.

The command should also be available as:

```bash
python -m blueprint_config generate ...
```

The Python distribution can expose the console command through `pyproject.toml`:

```toml
[project.scripts]
blueprint-config = "blueprint_config.cli:main"
```

### 9.2 Do not require a full Home Assistant installation merely to generate files

The core generator should be able to read the definition, copy/pass through native blueprint input syntax, inspect selector shapes needed for typing, and emit artifacts without requiring the entire Home Assistant package as a dependency.

When Home Assistant's Python package is available, the generator may optionally validate the synthesized blueprint using Home Assistant's own schema:

```python
from homeassistant.components.blueprint.schemas import BLUEPRINT_SCHEMA
```

That exact validation is useful during development, but Home Assistant itself remains the final authority when it loads the installed blueprint.

### 9.3 Preserve the input tree

If Home Assistant helpers are used, avoid relying on flattened input representations when layout/documentation information is needed. Preserve the original/validated `input` tree so input sections remain distinguishable from actual object-selector nesting.

### 9.4 Selector analysis is intentionally shallow

The generator needs to understand selector declarations only far enough to derive:

- a Python static type;
- scalar versus multiple value shape;
- recursive object structure; and
- optional representation conversions.

It should not duplicate selector-value validation.

---

## 10. Generated script blueprint

The generated blueprint contains no application behavior. Its only job is to collect selected inputs and return them as a mapping.

Conceptually:

```yaml
blueprint:
  name: Powerwall Export
  description: Configuration for scheduled Powerwall export behavior.
  domain: script
  input:
    # copied from definition
    ...

sequence:
  - variables:
      config:
        enabled: !input enabled
        min_soc: !input min_soc
        export: !input export

  - stop: Return blueprint configuration
    response_variable: config
```

The generated sequence should be mechanical and framework-owned.

---

## 11. Runtime discovery

The runtime adapter discovers configuration scripts by the installed generated blueprint path, not by script entity naming convention.

Home Assistant Core currently provides helpers such as:

```python
from homeassistant.components.script import scripts_with_blueprint

entity_ids = scripts_with_blueprint(
    hass,
    "blueprint_config/powerwall_export.yaml",
)
```

and the inverse helper:

```python
from homeassistant.components.script import blueprint_in_script
```

All dependence on these Home Assistant Core helpers should live behind one small framework adapter.

### 11.1 `hass` access

Using blueprint-based script discovery from PyScript requires access to Home Assistant's `hass` object. The framework should document the applicable PyScript requirement (`hass_is_global`) if this remains necessary in the implementation.

---

## 12. Instance cardinality

### 12.1 `instances: one`

Exactly one usable script instance must exist for the generated blueprint.

```text
number of discovered usable instances

0    -> configuration error + notification
1    -> load CONFIG
>1   -> configuration error + notification
```

The framework must never choose an arbitrary instance when more than one exists.

Example diagnostic:

```text
Blueprint configuration error: Powerwall Export requires exactly one
configuration script, but 2 were found:
script.powerwall_export and script.powerwall_export_test.
```

A cardinality error should also be logged. The consumer should not receive a fabricated default `CONFIG` object.

### 12.2 `instances: many`

Zero or more usable instances are valid initially:

```python
CONFIGS: tuple[RoomControlConfig, ...]
```

Each discovered script is called independently and converted into one configuration model object.

The source script entity ID may eventually be exposed as framework metadata, but should not be injected into the user's configuration schema merely to support discovery.

### 12.3 Usable-instance semantics

The Home Assistant discovery adapter should define "usable" in one place and handle disabled/unavailable/non-callable entities appropriately. The rest of the framework should not depend on Home Assistant's representation details.

---

## 13. Configuration retrieval

Each discovered configuration script is called and its response is returned directly to PyScript.

Conceptually:

```python
response = service.call(
    "script",
    service_name,
    return_response=True,
)
```

This is preferable to an event-based return path because it avoids:

- a custom event listener;
- correlation/request IDs;
- race handling;
- timeout bookkeeping; and
- unrelated listeners seeing configuration-return events.

The generated script behaves like a configuration function:

```text
PyScript ---- call ----> generated configuration script
         <--- dict -----
```

---

## 14. Validation philosophy

### 14.1 Home Assistant owns selector-value validation

Selector definitions already describe what values Home Assistant accepts and provide the GUI used to enter those values.

The framework should **not** duplicate constraints such as:

```text
number min/max
select choices
entity-selector syntax
boolean type
object field shape
```

in `attrs` or in a parallel validator hierarchy.

Design principle:

> Home Assistant validates configuration values. `blueprint-config` validates its framework contract and converts already-valid values into convenient Python representations.

### 14.2 What the framework still validates

The framework should check only things Home Assistant cannot own for it:

- `pyscript:` metadata syntax;
- required `module` and `instances` values;
- generated artifact naming constraints;
- expected configuration-instance cardinality;
- that a script response is a mapping;
- that fields required by the generated model are present;
- that recursive conversion succeeds; and
- compatibility/version mismatches between definition, generated files, and loaded configuration.

### 14.3 Cross-field semantic rules

Application semantics such as:

```text
start < end
minimum_soc < target_soc
```

should initially remain normal application checks rather than motivating a framework validation language.

---

## 15. Runtime model with `attrs`

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

Consumer code gets natural attribute access:

```python
CONFIG.min_soc
CONFIG.export.start
CONFIG.export.max_power
```

The implementation may construct these classes dynamically rather than emitting concrete implementation class source.

### 15.1 Conversion versus validation

Converters are appropriate when the desired Python representation differs from Home Assistant's selector result. For example, a Home Assistant time selector value may be converted from a string into:

```python
datetime.time
```

This is representation conversion, not revalidation of the selector's constraints.

### 15.2 Initial selector/type mapping

A conservative initial mapping can include:

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
| object with `multiple: true` | immutable collection of generated nested models |
| unknown/pass-through selector | `Any`, unless strict mode eventually requires an error |

---

## 16. Generated runtime module and `.pyi`

Generated runtime code and its type stub should have the same basename and live together in an importable PyScript module package:

```text
<config>/pyscript/modules/blueprint_config/generated/
    __init__.py
    powerwall_export.py
    powerwall_export.pyi
```

This fits PyScript's supported module mechanism and allows type-aware editors to treat the `.pyi` as the module's static interface while runtime Python executes the `.py` implementation.

### 16.1 Singleton stub

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

### 16.2 Multiple-instance stub

```python
class RoomControlConfig:
    ...


CONFIGS: tuple[RoomControlConfig, ...]
```

### 16.3 Why generate the stub separately

The runtime model may be constructed dynamically with `attrs`, but a language server cannot reliably infer the resulting attributes from runtime metaprogramming.

The generated `.pyi` gives Pylance/Pyright explicit knowledge of:

```python
CONFIG.min_soc
CONFIG.export.start
```

without requiring handwritten type declarations.

---

## 17. Build, install, and distribution model

Generation is a **developer/build-time activity**, not an end-user requirement.

A single generation step can produce both staged package artifacts and installed Home Assistant artifacts.

### 17.1 Staged package artifacts

For a source unit:

```text
pyscript/scripts/powerwall_export/
    powerwall_export.py
    blueprint_config.yaml
    #generated/
        powerwall_export.yaml
        powerwall_export.py
        powerwall_export.pyi
```

The staged files are convenient for:

- inspection;
- Git diffs;
- packaging;
- redistribution; and
- installing on another Home Assistant system without rerunning the generator.

They are not the local live copies used by PyScript/Home Assistant.

### 17.2 Installed artifacts

The generator also writes or installs identical content to the live locations:

```text
<config>/blueprints/script/blueprint_config/
    powerwall_export.yaml

<config>/pyscript/modules/blueprint_config/generated/
    powerwall_export.py
    powerwall_export.pyi
```

This deliberate duplication serves two different lifecycles:

```text
source definition
      |
      v
   generator
      |
      +--> source-local #generated/       package/distribution copy
      |
      +--> blueprints/script/...          installed HA copy
      |
      +--> pyscript/modules/...           installed runtime/type copy
```

### 17.3 Why generate twice?

For a developer's own Home Assistant system, only the installed copies are needed at runtime.

For a distributable PyScript package, the source-local `#generated/` copies allow the package author to ship ready-to-install generated artifacts. A recipient does not need:

- the generator;
- a development Python environment;
- Home Assistant's Python package available to the generator; or
- knowledge of how the schema was transformed.

The package can therefore be **build once, install many**.

### 17.4 Packaging options

A simple package can include:

```text
powerwall_export/
    powerwall_export.py
    blueprint_config.yaml        # optional for end users; useful for source distribution
    #generated/
        powerwall_export.yaml
        powerwall_export.py
        powerwall_export.pyi
```

An eventual `build` command could instead create an install-shaped distribution tree:

```text
dist/
└── powerwall_export/
    ├── blueprints/
    │   └── script/
    │       └── blueprint_config/
    │           └── powerwall_export.yaml
    └── pyscript/
        ├── scripts/
        │   └── powerwall_export/
        │       └── powerwall_export.py
        └── modules/
            └── blueprint_config/
                └── generated/
                    ├── powerwall_export.py
                    └── powerwall_export.pyi
```

That is an optional future packaging convenience; it is not required for the MVP.

### 17.5 Version-control policy

The canonical source files should be committed:

```text
powerwall_export.py
blueprint_config.yaml
```

For projects intended for redistribution, committing `#generated/` is reasonable because those files are part of the distributable artifact and let recipients install without regeneration.

For purely local projects, `#generated/` may be ignored if the developer prefers to regenerate build products.

The installed copies under global Home Assistant directories need not be treated as canonical source.

---

## 18. Jupyter workflow

The notebook and production PyScript code should use the **same import**:

```python
from blueprint_config.generated.powerwall_export import CONFIG
```

or:

```python
from blueprint_config.generated.room_control import CONFIGS
```

This avoids notebook-only typing declarations.

The CLI generator can be run from a JupyterLab shell terminal or invoked as a normal Python module.

When generation occurs while the same Jupyter kernel remains active, runtime code may need to be reloaded:

```python
import importlib
import blueprint_config.generated.powerwall_export as cfg

importlib.reload(cfg)
CONFIG = cfg.CONFIG
```

Pylance/Pyright may also need to notice the rewritten `.pyi`; that is an editor refresh issue, not a runtime design problem.

Ruff can lint/format Python, stub, and notebook source, but the `.pyi` exists primarily for static type tooling such as Pylance/Pyright.

---

## 19. Generator behavior

The generator should accept either a definition file or a directory tree. Each definition is self-contained.

Examples:

```bash
blueprint-config generate \
    /config/pyscript/scripts/powerwall_export/blueprint_config.yaml
```

and:

```bash
blueprint-config generate /config/pyscript/scripts
```

For each definition:

1. Load YAML.
2. Validate the small `pyscript:` metadata contract.
3. Derive artifact names from `pyscript.module`.
4. Build the complete script-blueprint structure.
5. Optionally pass it through Home Assistant's `BLUEPRINT_SCHEMA` when Home Assistant is importable.
6. Preserve the `input` tree for layout/documentation analysis.
7. Walk selectors only far enough to derive Python types and conversions.
8. Generate the script sequence that returns blueprint input values as one mapping.
9. Generate the runtime adapter.
10. Generate the matching `.pyi` stub.
11. Write all three artifacts under the source unit's `#generated/` directory.
12. Install/copy the blueprint into `<config>/blueprints/script/blueprint_config/` when an installation root is known.
13. Install/copy the runtime module and stub into `<config>/pyscript/modules/blueprint_config/generated/` when an installation root is known.
14. Optionally run format/lint checks on generated Python/stub files.
15. Report generated and installed paths plus any selector shapes typed as `Any` or otherwise unsupported.

No additional per-definition naming arguments should be required.

### 19.1 Possible commands

The initial CLI may only need:

```text
blueprint-config generate <file-or-directory>
```

Later, if useful, generation and installation can be split explicitly:

```text
blueprint-config build <file-or-directory>
blueprint-config install <package-or-directory>
```

The MVP should not add separate commands unless the workflow demonstrates a real need.

---

## 20. Lifecycle and refresh

The MVP lifecycle is intentionally simple:

- a developer edits `blueprint_config.yaml`;
- the developer runs the generator;
- the generator updates staged and installed artifacts;
- Home Assistant users create/edit configuration instances through the blueprint GUI;
- PyScript loads configuration during module/consumer initialization; and
- after configuration edits, an appropriate script/PyScript reload refreshes the configuration.

Automatic configuration-change watching can be added later if it provides meaningful ergonomic benefit.

Configuration model objects should be replaced on refresh rather than mutated.

---

## 21. Error reporting

The framework should make configuration failures conspicuous and actionable.

Errors should be both logged and, for conditions requiring user action, surfaced through a Home Assistant notification or repair-style mechanism where practical.

Initial errors include:

- malformed framework metadata;
- generated blueprint rejected by Home Assistant;
- zero instances when `instances: one`;
- multiple instances when `instances: one`;
- configuration script unavailable or not callable;
- missing/non-mapping script response;
- stale generated model versus returned structure; and
- conversion failure.

Messages should use the human-readable blueprint name while internal lookup continues to use the stable module-derived blueprint path.

---

## 22. Trust and security boundary

The generated script blueprint is framework-owned infrastructure. Its sequence should be generated and should simply expose blueprint inputs as a script response.

Because values arrive through Home Assistant's blueprint/selector system, the runtime model can normally trust their selector-level validity.

The framework still checks structural consistency so a stale, manually modified, or incompatible generated artifact fails clearly.

Secrets should remain outside this mechanism. A blueprint-created script is convenient configuration storage, not a secret-management system.

---

## 23. Compatibility boundary

The design intentionally distinguishes application-facing behavior from Home Assistant Python implementation details.

Sensitive dependencies include runtime blueprint-instance discovery through helpers such as:

```python
homeassistant.components.script.scripts_with_blueprint
```

Those calls should be isolated in one runtime adapter.

Optional exact blueprint validation through:

```python
homeassistant.components.blueprint.schemas.BLUEPRINT_SCHEMA
```

should likewise be isolated in the generator and must not become a mandatory dependency for package consumers.

If Home Assistant changes these APIs, the consumer-facing API (`CONFIG`, `CONFIGS`, generated models) should remain unchanged where possible.

---

## 24. End-to-end example

### 24.1 Source

```text
/config/pyscript/scripts/room_control/
    room_control.py
    blueprint_config.yaml
    #generated/
        room_control.yaml
        room_control.py
        room_control.pyi
```

Definition:

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

### 24.2 Generation and installation

```text
blueprint_config.yaml
      |
      +--> scripts/room_control/#generated/room_control.yaml
      +--> scripts/room_control/#generated/room_control.py
      +--> scripts/room_control/#generated/room_control.pyi
      |
      +--> blueprints/script/blueprint_config/room_control.yaml
      +--> pyscript/modules/blueprint_config/generated/room_control.py
      +--> pyscript/modules/blueprint_config/generated/room_control.pyi
```

### 24.3 Home Assistant UI

The user creates any number of scripts from the generated **Room Control** blueprint. Each script represents one room and is edited using Home Assistant's normal entity and number selectors.

### 24.4 PyScript runtime

```python
from blueprint_config.generated.room_control import CONFIGS

for config in CONFIGS:
    temperature = state.get(config.temperature_sensor)
    control_room(temperature, config.setpoint)
```

### 24.5 Distribution

A package author can ship the source unit together with `#generated/`. The receiving user or installer copies the staged generated files to the standard blueprint and module destinations. No schema regeneration is required on the recipient system.

---

## 25. MVP implementation plan

1. Adopt `blueprint-config` / `blueprint_config` naming throughout.
2. Implement metadata parsing for `module` and `instances`.
3. Implement discovery of `blueprint_config.yaml` from a file or recursive directory scan.
4. Build the complete Home Assistant script blueprint from the source definition.
5. Generate a script response mapping from every non-section input.
6. Implement basic selector/type analysis without duplicating selector validation.
7. Implement frozen dynamic `attrs` models.
8. Generate side-by-side runtime `.py` and `.pyi` files.
9. Write staged copies under the source unit's `#generated/` directory.
10. Install identical runtime/stub copies under `pyscript/modules/blueprint_config/generated/`.
11. Install the generated blueprint under `blueprints/script/blueprint_config/`.
12. Implement discovery through a small `scripts_with_blueprint()` adapter.
13. Implement `instances: one` and `instances: many` cardinality behavior.
14. Call configuration scripts with `return_response=True`.
15. Add Home Assistant diagnostics for singleton-cardinality failures.
16. Verify the same generated import from both Jupyter and a normal PyScript consumer.
17. Verify that a package copied from `#generated/` can be installed on a second system without running the generator.

### 25.1 Suggested first test definition

The first proof of concept should include:

- one boolean;
- one numeric input;
- one entity selector;
- one time selector;
- one object selector with two or three fields; and
- both `instances: one` and `instances: many` variants.

Test singleton discovery with zero, one, and two configuration scripts before expanding selector coverage.

---

## 26. Open design questions

### 26.1 Identity for multiple instances

Should the source script entity ID be exposed as:

```python
config.entity_id
```

kept outside the user model:

```python
ConfigInstance(entity_id=..., config=...)
```

or omitted unless explicitly requested?

### 26.2 Optional inputs

How should an omitted optional input appear in the generated model and stub? Likely approaches include:

```python
str | None
```

or omission only when Home Assistant's script expansion makes that possible. This should be determined from actual blueprint behavior.

### 26.3 Unknown selectors

When Home Assistant adds a selector the generator does not yet understand, should generation:

- pass it through and type it as `Any`; or
- fail with an explicit unsupported-selector error?

A pass-through `Any` fallback favors forward compatibility; a future strict mode could require complete typing.

### 26.4 Schema/generated-artifact versioning

Should generated artifacts carry a small framework/schema version marker so stale runtime files can be detected deterministically?

### 26.5 Refresh semantics

Is explicit reload-after-edit sufficient, or should the runtime eventually react automatically when relevant script configurations are reloaded?

### 26.6 Installation metadata

Should `#generated/` eventually contain a small manifest describing each staged file's install destination, or is the filename/module convention sufficient?

A manifest could make third-party packaging/install tooling simpler without changing runtime behavior.

---

## 27. Design principles

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
11. **Keep generation out of the Home Assistant runtime path.**
12. **Let source organization and PyScript import organization be different when PyScript's loader requires it.**
13. **Treat `#generated/` as package staging, not as the live import path.**
14. **Build once and allow distributed packages to install without regeneration.**
15. **Make Jupyter and production imports identical.**
16. **Prefer a small framework over a comprehensive duplicate of Home Assistant.**

---

## 28. Current platform references

The design has been discussed against these Home Assistant/PyScript facilities:

- Home Assistant blueprint schema and native `input:` metadata;
- Home Assistant selectors, including object selectors;
- Home Assistant script response data (`response_variable` / service responses);
- Home Assistant Core blueprint/script helpers such as `BLUEPRINT_SCHEMA`, `scripts_with_blueprint()`, and `blueprint_in_script()`;
- PyScript `hass_is_global` access;
- PyScript `modules/` for importable shared modules;
- PyScript recursive autoload behavior under `scripts/`; and
- PyScript's ignored `#` file/directory convention.

Exact Home Assistant/PyScript internal APIs should be verified against the target version during implementation and isolated behind framework adapters.

---

## 29. Recommended next step

Build the smallest vertical proof of concept around the finalized filesystem/build model:

```text
scripts/powerwall_export/
    powerwall_export.py
    blueprint_config.yaml
    #generated/
        powerwall_export.yaml
        powerwall_export.py
        powerwall_export.pyi

            generation/install
                    |
                    +--> blueprints/script/blueprint_config/powerwall_export.yaml
                    +--> pyscript/modules/blueprint_config/generated/powerwall_export.py
                    +--> pyscript/modules/blueprint_config/generated/powerwall_export.pyi
```

Then prove:

```text
one definition
    -> generated blueprint
    -> one GUI-created script instance
    -> discovered by blueprint identity
    -> script response
    -> attrs CONFIG
    -> Pylance-visible CONFIG fields
```

After that works, test `instances: one` error handling, `instances: many`, object-selector nesting, and installation of the staged `#generated/` files onto a second system without regeneration.
