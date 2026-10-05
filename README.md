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
        name="Speed", default=0, min=0, max=100, step=1,
        unit_of_measurement="%", mode="slider",
    )

settings = FanSettings(enabled=True, speed=25)
assert settings.enabled is True
assert settings.speed == 25.0
```

Number also supports `step="any"` and `translation_key`. Omitted selector options
are left to Home Assistant's defaults. Use `allow_none=True` to allow an absent
value without a default. Defaults fill absent/None values; explicit `False` and
`0` are preserved. `default=None` is not accepted.

Unknown constructor keywords raise `TypeError`; invalid declaration values are
reported through `get_build_diagnostics()` when the configuration class is
created. Current typing covers selector constructor arguments, not inference of
configuration-instance attributes. Full blueprint generation and other selectors
still have prototype limitations documented in [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).
