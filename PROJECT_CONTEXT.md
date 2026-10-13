# Project context: blueprint-config

Last inspected: 2026-10-13. This document is the starting point for a new AI conversation. It records the actual checkout separately from older designs and future work. Recent changes split selectors into individual modules while preserving their public imports and existing behavior. Boolean and Number retain their explicit typed constructors; Object now uses its declared EmbeddedObject type for rendering and conversion. Date and DateTime provide typed declarations, Python date/datetime conversion, and string defaults for generated YAML.

## Goal

Provide a Home Assistant GUI for configuring Pyscript automations through script blueprints. A user creates a script from a blueprint, chooses values with native selectors, and the script returns a configuration mapping. Python code consumes the configuration using named attributes and appropriate value conversions.

The broader design includes a supervisor that installs generated blueprints, evaluates configuration scripts, caches configuration, and reloads dependent Pyscript apps only when relevant data changes.

## Workspace and source of truth

- The source of truth is **this repository checkout**, identified by `pyproject.toml` and `src/blueprint_config/`. Its absolute location may differ across machines and worktrees.
- All local file references in these root-level handoff documents are relative to the repository root.
- Read [agent.md](agent.md) for working instructions; [AGENTS.md](AGENTS.md) is the discovery entry point.
- A separate conversation workspace was used during initial development. It is optional, is not the source checkout, and is not required on another machine. Do not scaffold a duplicate implementation there.
- Initial inspection baseline: commit `b0d09c5` (`Started adding numeric selector`). This is historical provenance, not the current HEAD; inspect Git for the current state.
- [docs/example.md](docs/example.md) was a pre-existing untracked draft at initial inspection and was left unchanged. Check current Git status rather than assuming it is still untracked.
- On each machine, run `uv sync --dev` in the repository root to recreate the development environment. Do not transfer `.venv` between operating systems. Use the `uv run` commands below; no platform-specific environment activation or executable path is needed.

## What the code actually does

The checkout is an early **Python-to-blueprint generator and configuration-object prototype**. It does not currently implement the earlier YAML-to-generated-attrs runtime design.

A developer declares a `BlueprintConfig` subclass with blueprint metadata and field objects such as `Boolean`. Class construction registers the class and validates field declarations. Instance construction consumes supplied values/defaults and collects load diagnostics. `build_blueprint()` returns YAML containing inputs and a script intended to return the selected values.

There is no `attrs` dependency or frozen configuration implementation in this checkout. Current `BaseConfig` instances are mutable and have no custom structural equality implementation. Do not assume `new_config != old_config` on these objects implements the supervisor's intended semantic comparison.

| File | Current responsibility/status |
| --- | --- |
| [src/blueprint_config/config.py](src/blueprint_config/config.py) | `BaseConfig` registration, declaration inspection, construction, diagnostics, `from_dict`; `BlueprintConfig` metadata/YAML generation; `EmbeddedObject` rendering. |
| [src/blueprint_config/items.py](src/blueprint_config/items.py) | `BlueprintItem`, `FieldItem`, argument consumption and validation; compatibility import for `InputSection`. |
| [src/blueprint_config/fields/](src/blueprint_config/fields/) | One module per selector (`boolean.py`, `date.py`, `datetime.py`, `number.py`, `object.py`, `time.py`), plus `input_section.py` for `InputSection`, re-exported by `fields/__init__.py`. `Boolean`, `Number`, `Date`, and `DateTime` have explicit typed keyword-only constructors; `Time` and `Object` retain the older API. `Number` is exported alongside `Boolean` and `Object`. |
| [src/blueprint_config/diagnostic.py](src/blueprint_config/diagnostic.py) | Severity-filtered diagnostics and a context-manager path mechanism. |
| [src/blueprint_config/types.py](src/blueprint_config/types.py) | `MISSING`, `Status`, `ParamTypeChk`, `InputRef`. |
| [src/blueprint_config/util.py](src/blueprint_config/util.py) | PyYAML dumper preserving field order, multiline strings, and `!input` references. |
| [bathroom_fan_lights.yaml](bathroom_fan_lights.yaml) | Hand-authored script blueprint example: light/occupancy/scene entities and day start/end times; returns a mapping. |
| [test/](test/) | pytest and inline-snapshot prototype tests; partly out of sync with current source. |
| [test/config_object/REQUIREMENTS.md](test/config_object/REQUIREMENTS.md) | Partial behavioral requirements; unfinished entries and duplicate IDs. |
| [blueprint-config-design.md](blueprint-config-design.md) | Historical v0.6 design, revised 2026-08-17; valuable rationale but not the current implementation specification. |
| [docs/example.md](docs/example.md) | Pre-existing short introductory draft. |
| [pyproject.toml](pyproject.toml) | Python >=3.14, PyYAML runtime dependency, uv build system, pytest/inline-snapshot/Ruff development tools. |

Not implemented in this checkout: Home Assistant script discovery/execution, configuration-specific runtime loaders, supervisor services/cache, blueprint file installation, script/app reload coordination, multi-instance runtime loading, or a working CLI entry function. The declared `blueprint-config = "blueprint_config:main"` entry point has no corresponding `main` in the package.

`blueprint_path` currently means an absolute filesystem path (if supplied). Generation returns a string; it does not write that path. Historical runtime examples use a relative identity such as `pyscript/bathroom_fan_lights.yaml`; these are different concepts that still need a clear interface.

## Verified baseline and source-review findings

### Current verification baseline (2026-10-13)

The full suite passes: **270 passed**, including **80 Date/DateTime cases**.
Ruff checks for `src` and `test` and diff whitespace checks pass. Tests ran with
`uv run python -m pytest -q -p no:cacheprovider`. This supersedes earlier baselines
below. Home Assistant and Pyscript runtime behavior remains unverified.

### Date and DateTime selectors (2026-10-13)

Added `fields/date.py` and `fields/datetime.py`, exported through `fields` and the
package root as `Date` and `DateTime`. Both have explicit keyword-only metadata,
default, allow_none, and section parameters, with no selector-specific options,
matching the [HA selector documentation](https://www.home-assistant.io/docs/blueprint/selectors/#date-selector).

Date accepts calendar-date strings (`YYYY-MM-DD`) or Python date values, excluding
datetime objects. DateTime accepts Python datetime values or calendar-date/time
strings separated by a space or `T`, with hours/minutes, optional seconds and
1–6 fractional digits, and optional `Z`/numeric offsets. It rejects date-only
values and hours outside 00–23. Python 3.14's parser can normalize 24:00 to the next
day, so the selector explicitly guards against that silent date change.
Runtime conversion returns date/datetime objects, preserving offsets and
microseconds without inferring a timezone. Defaults are validated at class build
and normalized to ISO strings for YAML; invalid defaults produce diagnostics and
become MISSING. None handling follows the existing default-first convention.
Malformed runtime values record a diagnostic and raise TypeError/ValueError.

The shared parameterized suite `test/fields/test_date_datetime.py` covers imports,
constructor signatures, defaults, None/missing values, invalid declarations and
runtime values, leap dates, formatting, precision/offsets, YAML serialization,
sections, and embedded objects. README includes usage and the accepted formats.
No dependencies were added. Live HA/Pyscript execution and timezone-aware values
in the HA UI were not verified. The existing Time selector and general blueprint
sequence limitation remain unchanged.

### InputSection nesting validation and test expansion (2026-10-12)

InputSection now records a build ERROR when assigned to another section, naming the nested section. This matches the [HA blueprint schema](https://github.com/home-assistant/core/blob/dev/homeassistant/components/blueprint/schemas.py), which permits only ordinary inputs inside sections. The check runs after all declarations are bound and applies regardless of declaration order or collapsed state. Missing-default checks and custom configuration validation still run. As with other build errors, callers inspect `get_build_diagnostics()`; generation is not changed to raise exceptions.

The dedicated `test/config_object/test_input_section.py` suite now has **30 passing cases**. Added coverage for nesting, combined diagnostics, invalid metadata and section arguments, unknown-argument warnings, omitted/empty metadata, multiline descriptions and collapsed YAML serialization, multiple-section membership and ordering, flat loaded values and input references, and compatibility imports. Full suite: **190 passed**. Ruff and diff whitespace checks pass. No live Home Assistant or Pyscript verification was performed. References to undeclared sections and general declaration inheritance/reuse remain outside this change; full HA schema parity is not claimed.

### Collapsed-section defaults (2026-10-12)

A section with `collapsed=True` now records one build ERROR for each member without a default, naming the input and section. Checks run after all declarations are validated so class attribute order does not affect results. Omitted or false `collapsed` does not require defaults. Explicit `MISSING` and `allow_none=True` without a default do not satisfy the rule; false, zero, and empty collection defaults do. This follows the [HA input section definition](https://www.home-assistant.io/docs/blueprint/schema/#blueprint-input-sections). Errors are available through `get_build_diagnostics()`; blueprint generation retains the existing behavior of not raising for build diagnostics.

Verification: **167 passed**, Ruff and diff whitespace checks pass. Coverage includes both declaration orders, one diagnostic per offending member, unrelated inputs, expanded and empty sections, and false/zero/empty defaults. No live Home Assistant or Pyscript verification was performed.

### InputSection module split (2026-10-12)

Moved `InputSection` into `fields/input_section.py`, exported through `fields` and the package root. It remains a `BlueprintItem`; grouping and generated YAML are unchanged. Imports through `items` and `config` remain compatible. Section type validation resolves the concrete class at validation time, preserving its previous applicability to fields and blueprint items. Object resolves its EmbeddedObject validation dependency locally to avoid the config/fields import cycle.

Verification: **161 passed**; Ruff checks pass. Import smoke checks confirm class identity across new and existing paths and resolvable Boolean/Number section annotations. Used the existing virtual environment because uv could not access its external cache. No Home Assistant or Pyscript runtime verification was performed.

### Number selector validation (2026-10-12)

Number now requires both bounds for explicit slider mode and a numeric step of at least `0.001` (or `"any"`), matching the [HA Number selector implementation](https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/selector.py). Additional library declaration checks reject reversed bounds and defaults outside the inclusive bounds. Conversion checks bounds after default/None resolution, records a diagnostic, and raises `ValueError` for out-of-range values. Step does not round values or constrain them to multiples. Equal bounds remain valid.

The Python contract intentionally retains strict int/float inputs (excluding bool and numeric strings), float outputs, and shared default/allow_none handling. Omitted selector options remain omitted for HA defaults. The earlier translation_key exclusion remains in force. `read_only` is intentionally excluded, not pending implementation: the user tested it in the blueprint editor and reported that it was not enforced. HA documents it for integration data-entry flows, whose form explicitly disables read-only selectors; the blueprint editor does not perform that translation. The user approved excluding it from this library. It was never added to the Number constructor or YAML output. See [Displaying read-only information](https://developers.home-assistant.io/docs/data_entry_flow_index/#displaying-read-only-information) and the [config-flow form implementation](https://github.com/home-assistant/frontend/blob/dev/src/dialogs/config-flow/step-flow-form.ts). Exact general-selector schema parity is not claimed.

Number tests now contain **65 passing cases**, covering slider requirements, optional bounds, inclusive endpoints, equal/reversed ranges, default validation, runtime diagnostics, the step threshold, off-step values, and malformed declarations. Full suite: **161 passed**. Ruff checks and diff whitespace checks pass. README documents the updated contract. No live Home Assistant or Pyscript verification was performed.

### Boolean selector test expansion (2026-10-12)

Expanded `test/fields/test_boolean.py` from 18 to **38 passing cases**. Added default precedence with both allow_none settings, explicit MISSING defaults, omitted/empty metadata, Boolean defaults through YAML serialization, invalid section and declaration values, invalid runtime values with defaults, actual section rendering/loading, and optional embedded Boolean values. No implementation changes were needed. Full suite: **124 passed**; Ruff and diff whitespace checks pass. Number coverage is unchanged.

### Object selector test expansion (2026-10-12)

Expanded Object coverage from 10 to **45 passing cases**, adding default precedence over allow_none, explicit-value overrides, input/default mutation isolation, empty mapping/list behavior, required-field diagnostic context, invalid declaration options, unknown-option warnings, independent label/description rendering, malformed runtime values, embedded conversion errors, repeated nested objects, and input-section integration. This expansion changes tests only, with no further selector implementation changes.

Full suite: **104 passed, 1 error**. The sole error remains the pre-existing missing inline snapshot in `test_button_diagnostics_simple`; it was not regenerated. Ruff and diff whitespace checks pass. Tests ran through the existing virtual environment. These checks cover the Python generator/converter; live Home Assistant and Pyscript behavior remains unverified. Full Object schema validation and nested diagnostic propagation are still outside this coverage.

### Object selector recursion fix (2026-10-11)

Object now consumes and validates `object_type` as an `EmbeddedObject` subclass, keeping `_parent_class` as the containing class. Rendering and conversion use the embedded type, including nested Object fields. Missing or invalid types produce build diagnostics and raise a clear TypeError if rendering/conversion is attempted. Object defaults (dict/list) are consumed, and None resolution follows the shared default/allow_none behavior. Label and description field names retain their strings instead of becoming booleans; empty options are omitted. The Object test default was corrected to the field's list value rather than an outer configuration mapping.

Verification: **69 passed, 1 error** in the full suite; the remaining error is the pre-existing missing inline snapshot in `test_button_diagnostics_simple`. Ruff passes. Regression coverage includes generated object fields, single/repeated conversion, defaults, False and empty-list preservation, optional values, nested objects, and invalid object types. Used the existing virtual environment directly because uv's external cache was sandbox-inaccessible. No Home Assistant or Pyscript runtime verification was performed. Full Object schema/value validation remains future work.

### Selector module split (2026-10-11)

Replaced `fields.py` with a `fields/` package containing one module per selector. Shared behavior remains in `items.py` and shared types remain in `types.py`. Existing `blueprint_config.fields` selector imports and top-level exports are preserved; `Time` remains available through `blueprint_config.fields` without adding a new top-level export. Selector class bodies are unchanged, including the unfinished Object implementation.

Full-suite results immediately before and after the refactor: **59 passed, 1 failed, 1 error**. The failure is Object's recursive blueprint rendering; the error is a missing inline snapshot in `test_button_diagnostics_simple`. Existing tests required no import or snapshot changes. Ruff passes, and an import smoke check verified all four individual modules and their re-exports. No Home Assistant or Pyscript runtime verification was performed.

### Historical verification (2026-10-04)

The older failures listed below are historical and are superseded by the current test results above.

The verification baseline below was obtained on macOS on 2026-10-04 using the existing virtual environment. The equivalent portable command, run from the repository root, is:

```sh
uv run python -B -m pytest -q -p no:cacheprovider
```

Last full-suite result before translation_key removal: **57 passed, 7 failed**, exit status 1. The original four collection errors caused by Number's unhashable validator are fixed. Remaining failures are the input-section placeholder, five obsolete diagnostic tests, and unfinished Object argument handling.

Equivalent portable command for the focused run:

```sh
uv run python -B -m pytest -q -p no:cacheprovider test/fields/test_boolean.py test/fields/test_number.py test/config_object/test_simple_config.py
```

After translation_key removal: **55 passed** (its obsolete validation case was removed). Ruff checks pass for `src` and `test`. Windows execution has not been verified. No static type checker or live IDE completion test has been run; tests verify public constructor signatures and resolvable annotations.

### Typed selector API decision (2026-10-04)

The user authorized explicit typed selector classes, accepting repeated public declarations while sharing behavior. Boolean and Number now expose keyword-only constructor parameters rather than accepting arbitrary keyword arguments. Unknown keywords raise TypeError immediately; invalid declared values still produce build diagnostics when the owning configuration class is created. Selectors are still bound/validated by configuration class creation before conversion/rendering uses their options.

Number supports min/max, positive numeric step or `"any"`, unit_of_measurement, and mode (`"box"`/`"slider"`). Omitted options remain omitted so HA supplies its defaults. Numeric annotations use `float`, which permits integer arguments under Python typing; runtime checks accept int/float and reject bool. Number conversion returns float. Boolean preserves explicit False. Both share default/None resolution: an explicit non-None value wins, then the declared default, then allow_none; otherwise conversion records an error and raises ValueError. MISSING is distinct from None; `default=None` is invalid (use allow_none=True).

The user subsequently requested removal of `translation_key`. Although Home Assistant supports this option in integration contexts, it is useless for this library's standard blueprint editor: that editor supplies no selector translation lookup, and blueprint names/descriptions remain literal. The option is omitted from the constructor, declaration checks, and YAML rendering; use literal unit labels. See the [blueprint editor source](https://github.com/home-assistant/frontend/blob/dev/src/panels/config/blueprint/blueprint-generic-editor.ts). Do not reintroduce it solely to mirror the general selector schema.

`Missing` and `MISSING` are exported, and the package has a `py.typed` marker. Constructor typing is implemented; typed descriptors for configuration-instance attribute inference remain future work. Generic declaration validation now supports multiple exact numeric types and immutable choice tuples. Existing Boolean tests were updated to the current binding/diagnostic API; the former unknown-keyword warning test now checks TypeError. Historical snapshots were not regenerated.

Number options were checked against [Home Assistant selector documentation](https://www.home-assistant.io/docs/blueprint/selectors/#number-selector). This does not establish validity of the complete generated blueprint, whose pre-existing sequence/section issues remain below.

Remaining issues (source inspection and the full test run):

- `test_input_section.py` ends with an unconditional `assert False`.
- Diagnostic tests call removed methods or old signatures and use `child()` as though it returns a diagnostics instance rather than a context manager.
- `_generate_blueprint_sequence()` returns a mapping already containing `sequence`; `build_blueprint()` wraps it under another `sequence`. Existing snapshots preserve this extra nesting, unlike the hand-authored example's sequence list.
- `InputSection.selector()` returns an `inputs` wrapper, then `render_field()` wraps it under `input`. Check this against the intended section shape before blessing snapshots.
- `BaseConfig` field discovery examines the concrete class dictionary, so inherited-field behavior is not established.

These are investigation starting points, not authorization to fix all of them during unrelated work. No Home Assistant instance was contacted, no generated blueprint was loaded into HA, and no Pyscript runtime compatibility was verified.

## Design history and how to interpret it

The user provided three exported chats as external PDFs. They are not checked into this repository; the summaries below provide the handoff context without requiring the original files. If exact historical excerpts are needed, ask the user for the named document rather than assuming it exists on the current machine. They include proposals, corrections, working experiments, and references to attachments that are not themselves reproduced as complete source files in the PDFs. Do not claim the old runtime is in this repository merely because the chats discuss working code.

### Initial configuration design (August 11 onward)

External source: `PyScript Configuration Blueprint.pdf` (274 pages).

The discussion moved from Python declarations toward native YAML as the canonical schema, with generated concrete frozen `attrs` classes. It established script responses instead of a custom event response protocol, discovery by blueprint identity, nested/repeated data, time/duration conversion, Jupyter completion, and application-owned defaults.

Framework metadata proposed `instances: one|many`. Singleton loading should not silently choose among multiple scripts; cardinality notifications were discussed. Recursive `apply_defaults()` was developed around exact configuration types, replacing only `None` and preserving valid false values, using `attrs.evolve()`. Explicit loading replaced an exported global `CONFIG`. Concrete generated `.py` classes reduced the need for separate `.pyi` files.

Some positions changed within this chat: a blanket assumption that HA validates every stored selector value was questioned; nested object support was first deferred and later reconsidered. Treat these as evolving discussions, not universal guarantees.

### Pyscript implementation lessons (August 20 onward)

External source: `Write PyScript Blueprint Structure.pdf` (62 pages).

Testing exposed problems with interpreted classmethods and cross-module inheritance. The later API used ordinary frozen attrs classes, a blueprint-path class attribute, generic module functions, and a configuration-specific wrapper with a concrete return annotation:

```python
from blueprint_config.bathroom_fan_lights import (
    load_config,
    is_my_config_service,
)
```

The user combined normalization and validation into one optional `processor`: it returns a configuration or raises an exception. The change handler listens for script service registration and checks the service's current blueprint inside the handler. It must not permanently capture the old script service name, because the user may replace the configuration script.

The chats distinguish entity IDs from service names, using registry helpers for that mapping. These integration helpers are absent from this checkout. The classmethod/inheritance limitations apply to the historical interpreted Pyscript runtime; they do not automatically prohibit the current ordinary-Python generator architecture.

### Supervisor design (August 31)

External source: `Blueprint supervisor design.pdf` (13 pages).

The later discussion makes the supervisor the configuration provider:

1. An app/converter registers generated blueprint YAML.
2. Compare content with the installed blueprint; only a real change causes a write.
3. Batch/debounce Home Assistant script reloads.
4. Run the resulting configuration script and compare its result with cached configuration.
5. If configuration changed, update the cache before reloading dependent apps.
6. The restarting app gets the cached new configuration, allowing the system to settle.

The two change detectors are deliberately separate. Editing a description can change blueprint YAML while leaving runtime configuration equal. A getter should not itself trigger a reload; first retrieval establishes the baseline. Cache lifetime relative to app/supervisor reloads was left to resolve.

The final assistant recommendation was to return plain mappings across service boundaries rather than YAML or base64 pickle. The export does not show explicit user acceptance of the final serialization choice. Do not implement pickle based solely on the earlier question about it.

### Reconciling history with this checkout

The checked-in v0.6 document predates both the Pyscript API corrections and supervisor discussion. The current source uses Python field declarations, custom classes, and build/load diagnostics instead of the historical YAML-to-attrs path. The exact decision that produced this newer implementation is not captured by the supplied excerpts. Preserve the current direction and ask only when a task requires choosing between architectures.

## Decisions still needed when implementation reaches them

- Is the Python declaration API now the long-term canonical schema? How should it relate to any existing live attrs-based runtime outside this repository?
- Should runtime configuration use these custom classes, frozen attrs classes, or plain mappings? Which normalized representation provides semantic equality across reloads?
- Where does the supervisor run, how does its cache survive dependent app reloads, and how are dependent app identities registered?
- Does comparison occur before or after defaults and application processing? Who owns those operations when the supervisor retrieves data?
- How are missing, disabled, deleted, invalid, or ambiguous configuration scripts handled? Registration events alone do not settle deletion handling or whether an existing app keeps its last valid configuration.
- What are the supported HA/Pyscript versions and execution environments? Python >=3.14 in this package is not a verified HA runtime compatibility statement.
- What is the first supported selector set, object nesting contract, and multi-instance API?
- How do absolute installation paths relate to blueprint-relative identities, and who performs writes/reloads?

## Suggested next implementation sequence

This is a proposed sequence, not work already authorized or completed:

1. Resolve remaining test failures against intended behavior; package importability is restored and the current baseline is recorded above.
2. Reconcile tests and partial requirements with the Python declaration API; verify generated sequence and section shapes independently of snapshots.
3. Complete a small end-to-end example of declaration, blueprint generation, returned mapping, and Python configuration construction.
4. Resolve the runtime/generator boundary using the user's existing live Pyscript code if available.
5. Implement the supervisor around proven retrieval and equality behavior, including unchanged-content convergence and failure handling.

## Keeping future conversations aligned

Maintain this document as implementation advances. Record confirmed decisions with their rationale, remove resolved issues from the active baseline, and distinguish local Python tests from live HA/Pyscript verification. Retain the old design document for history unless explicitly revising it; do not use its old implementation checklist as an automatic work order.
