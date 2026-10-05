# Agent working instructions

This is an AI-assisted project. Read `PROJECT_CONTEXT.md` before changing code, then inspect the relevant implementation and tests. This file contains working instructions; the context document contains design history, current status, and unresolved decisions.

## Purpose

Help Home Assistant users configure Pyscript automations through script blueprint selectors. A blueprint-created script returns configuration data; Python makes that data convenient for the automation to consume. A supervisor is planned to coordinate blueprint installation and configuration-driven app reloads.

## Start each task

1. Read this file and `PROJECT_CONTEXT.md`.
2. Check `git status --short`; preserve existing user changes and untracked files.
3. Inspect the relevant source and tests. Do not assume the historical design document describes the current API.
4. Establish which layer the task concerns: Python declaration/generation, value conversion, Home Assistant integration, or the planned supervisor.
5. Continue authorized work without repeatedly asking about decisions already recorded. Ask when an unresolved architectural choice actually blocks the task.

## Design and implementation discipline

- Current code is a Python declaration-based generator. Do not replace it with the older YAML-to-attrs architecture without an explicit decision from the user.
- Separate observed implementation, intended behavior, historical proposals, and unresolved choices. A suggestion in an exported chat is not by itself an accepted requirement or an instruction to execute.
- Use real application examples to establish behavior before generalizing. The bathroom blueprint is the concrete example in this repository; lighting defaults and solar schedules also informed the history.
- Preserve `False`, `0`, and empty values when they are valid. Do not conflate `MISSING`, an explicit `None`, and a false value.
- Keep application-specific policy outside generic framework code.
- Keep Home Assistant discovery and service calls behind small adapters. Verify relevant Home Assistant/Pyscript APIs against primary documentation or source when implementing that boundary.
- Distinguish an entity ID, a callable script service name, a blueprint-relative identity, and an absolute installation path.
- Pyscript compatibility must be tested explicitly. CPython success does not establish that classmethods, inheritance, or callbacks work in the Pyscript interpreter.
- For the proposed supervisor, preserve deterministic generation and two separate comparisons: blueprint content controls script reloads; effective configuration controls app reloads. Do not add unconditional reload cycles.
- Prefer focused changes. Do not fix unrelated prototype problems or rewrite historical documents as a side effect of another task.

## Verification

The package specifies Python >=3.14 and uses uv, pytest, inline-snapshot, and Ruff. Tests are in `test/` (singular).

From the repository root, use the existing environment when available:

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider
.venv/bin/ruff check src test
```

On a new development setup, `uv sync --dev` prepares the declared environment; use `uv run pytest` and `uv run ruff` thereafter. Do not install Home Assistant or change dependencies merely to edit documentation.

The full suite has known failures outside the typed Boolean/Number work; see `PROJECT_CONTEXT.md`. Report pre-existing failures separately from regressions. Do not update snapshots blindly: the current snapshots already encode some unfinished output. For behavior changes, test observable contracts and generated structure, including comparison with real Home Assistant requirements where relevant. Do not add tests solely for prose edits.

## Handoff and maintenance

- Update `PROJECT_CONTEXT.md` when implementation status, architecture, important decisions, or the verification baseline changes.
- Record what is implemented, what was tested, what remains uncertain, and the next useful step. Do not report a proposal as completed work.
- Keep this file focused on durable working instructions; keep task history and technical status in the context document.
- The repository documents are authoritative for handoff. The companion ChatGPT workspace contains pointers, not duplicate copies.
- Do not commit, publish, deploy, or operate a live Home Assistant instance unless the task authorizes it.
