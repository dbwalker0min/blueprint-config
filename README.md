# blueprint-config
A configuration tool for pyscript based on Home Assistant blueprints.


## Typed selector declarations

Boolean, Number, Date, and DateTime expose explicit keyword-only parameters for editor completion:

```python
from blueprint_config import BlueprintConfig, Boolean, Number


class FanSettings(BlueprintConfig):
    blueprint_name = "Fan settings"

    enabled = Boolean(name="Enabled", default=False)
    speed = Number(
        name="Speed",
        default=0,
        min=0,
        max=100,
        step=1,
        unit_of_measurement="%",
        mode="slider",
    )


settings = FanSettings(enabled=True, speed=25)
assert settings.enabled is True
assert settings.speed == 25.0
```

Number also supports `step="any"`. Omitted selector options
are left to Home Assistant's defaults. Use `allow_none=True` to allow an absent
value without a default. Defaults fill absent/None values; explicit `False` and
`0` are preserved. `default=None` is not accepted.

Number bounds are inclusive and apply to both defaults and supplied values.
Declarations require `min <= max` when both bounds are present; explicit
`mode="slider"` requires both bounds. Numeric `step` must be at least `0.001`.
Step controls UI increments: values are not rounded or required to be multiples
of the step. Invalid Number types, out-of-range values, and required `None`
values record load errors and produce `MISSING` without raising. Loading also
continues after omitted required fields, storing `MISSING` for them. Inspect
`get_load_diagnostics()` after construction to report errors before using the
configuration. Other selectors still have exception-based conversion paths.
Python inputs remain strictly integers/floats (excluding booleans and numeric
strings), and conversion returns a float. Omitted mode and step are left to HA:
slider with both bounds, box otherwise, and a default step of 1.

Number reports unsupported positional and keyword arguments as build errors;
they are ignored, while supported options remain explicit and keyword-only.
Boolean, Date, and DateTime still raise `TypeError` for unsupported constructor
arguments. Invalid declaration values are reported through
`get_build_diagnostics()` when the configuration class is created.
Current typing covers selector constructor arguments, not inference of
configuration-instance attributes. Full blueprint generation and other selectors
still have prototype limitations documented in [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).

`translation_key` is intentionally omitted. Although Home Assistant supports it
for selectors in integration contexts, it is ineffective in the standard blueprint
editor, which does not supply the selector translation lookup. Use a literal
`unit_of_measurement`; blueprint input names and descriptions also remain literal.
See the [blueprint editor implementation](https://github.com/home-assistant/frontend/blob/dev/src/panels/config/blueprint/blueprint-generic-editor.ts).

`read_only` is also intentionally omitted: the blueprint editor does not enforce
it. Home Assistant documents this option for [integration data-entry flows](https://developers.home-assistant.io/docs/data_entry_flow_index/#displaying-read-only-information),
where the surrounding form disables the selector. It is not a supported option
in this library's blueprint workflow.

## Date and DateTime

```python
import datetime as dt

from blueprint_config import BlueprintConfig, Date, DateTime


class Schedule(BlueprintConfig):
    blueprint_name = "Schedule"

    day = Date(name="Day", default=dt.date(2026, 10, 13))
    start = DateTime(name="Start", allow_none=True)


schedule = Schedule(start="2026-10-13 09:30:00")
assert schedule.day == dt.date(2026, 10, 13)
assert schedule.start == dt.datetime(2026, 10, 13, 9, 30)
```

Both selectors accept `name`, `description`, `default`, `allow_none`, and
`section`. They emit `date: {}` and `datetime: {}`, matching the
[Home Assistant selectors](https://www.home-assistant.io/docs/blueprint/selectors/#date-selector).

`Date` accepts a `YYYY-MM-DD` string or Python `datetime.date` and returns a
`date`. It rejects `datetime` objects rather than discarding their time.
`DateTime` accepts Python `datetime.datetime` or a string with a calendar date,
a space or `T`, and `HH:MM`, optionally followed by seconds and 1–6 fractional
second digits. Strings may include `Z` or a `±HH:MM` offset (also supporting offset seconds
and fractions emitted by Python datetime values). Conversion preserves
supplied offsets and microseconds; values without an offset stay naive. A date
without a time is rejected, and hours must be in `00–23`.

Defaults accept the same values and are normalized to ISO strings for YAML
(`YYYY-MM-DD` or `YYYY-MM-DD HH:MM:SS`, retaining fractions/offsets when present).
Invalid defaults produce build diagnostics and are omitted from generated inputs.
Missing or `None` values use the default first, then `allow_none`. An empty string
is invalid, not missing. Invalid runtime types raise `TypeError`; malformed dates
or times raise `ValueError`; both record a load diagnostic. As with other fields,
an omitted required value records a load diagnostic during configuration loading.

Tests cover Python conversion and generated inputs. Live Home Assistant/Pyscript
execution and timezone-aware values in the Home Assistant UI remain unverified.
