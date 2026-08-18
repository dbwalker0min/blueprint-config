import datetime as dt
from collections.abc import Mapping
from typing import Any

import attrs.validators as val
from attrs import field, frozen
from stubs.pyscript_builtins import pyscript_compile

from blueprint_config import load_one, convert_time


@frozen
class LightConfig:
    light: str = field(validator=val.instance_of(str))
    button: str | None = None
    brightness_high: float | None = None
    brightness_low: float | None = None
    bright_start: dt.time | None = field(
        default=None,
        converter=convert_time,
    )
    bright_end: dt.time | None = field(
        default=None,
        converter=convert_time,
    )


@frozen
class LightControlConfig:
    lights: tuple[LightConfig, ...]
    default_brightness_high: float
    default_brightness_low: float
    default_bright_start: dt.time = field(converter=convert_time)
    default_bright_end: dt.time = field(converter=convert_time)


#@pyscript_compile
def _from_response(data: Mapping[str, Any]) -> LightControlConfig:
    log.info(data)
    return LightControlConfig(
        lights=tuple([LightConfig(**item) for item in data["lights"]]),
        default_brightness_high=data["default_brightness_high"],
        default_brightness_low=data["default_brightness_low"],
        default_bright_start=data["default_bright_start"],
        default_bright_end=data["default_bright_end"],
    )


CONFIG = load_one(
        blueprint_path="pyscript/light_control.yaml",
        factory=_from_response
)
