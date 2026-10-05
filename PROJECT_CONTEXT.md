# Project context: blueprint-config

Last inspected: 2026-10-04. This document is the starting point for a new AI conversation. It records the actual checkout separately from older designs and future work. Recent changes implement explicit typed Boolean and Number constructors, omit ineffective blueprint translation keys, and make these handoff instructions portable across checkouts.

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
| [src/blueprint_config/items.py](src/blueprint_config/items.py) | `BlueprintItem`, `FieldItem`, argument consumption and validation, `InputSection` grouping. |
| [src/blueprint_config/fields.py](src/blueprint_config/fields.py) | `Boolean` and `Number` have explicit typed keyword-only constructors; `Time` and `Object` retain the older API. `Number` is exported alongside `Boolean` and `Object`. |
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
- Object rendering still has assignment expressions that capture a comparison result instead of the intended value. The corresponding Boolean, Number, and shared validator problems were fixed.
- `Object` uses the containing `_parent_class` for conversion/rendering instead of consuming the test's `object_type=EmbeddedObjectSubclass` argument; object-field behavior is unfinished.
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
