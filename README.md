# blueprint-config
A configuration tool for pyscript based on Home Assistant blueprints.


## Typed selector declarations

Boolean and Number expose explicit keyword-only parameters for editor completion:

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
of the step. Out-of-range values record a load diagnostic and raise `ValueError`.
Python inputs remain strictly integers/floats (excluding booleans and numeric
strings), and conversion returns a float. Omitted mode and step are left to HA:
slider with both bounds, box otherwise, and a default step of 1.

Unknown constructor keywords raise `TypeError`; invalid declaration values are
reported through `get_build_diagnostics()` when the configuration class is
created. Current typing covers selector constructor arguments, not inference of
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
