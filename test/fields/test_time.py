import datetime as dt
import inspect
from typing import get_type_hints

import pytest
import yaml

from blueprint_config import (
    MISSING,
    BlueprintConfig,
    Diagnostics,
    InputSection,
    dump_yaml,
)
from blueprint_config.fields import Time

pytestmark = pytest.mark.review_required


def bind(field):
    class Config(BlueprintConfig):
        blueprint_name = "Time settings"
        value = field
        later = Time(default="00:00:00")

    return Config


@pytest.mark.reviewed(False)
@pytest.mark.parametrize("value", ["13:30:45.123456", dt.time(13, 30, 45, 123456)])
def test_time_conversion_and_defaults_preserve_precision(value):
    config_type = bind(Time(default=value))
    assert config_type.get_build_diagnostics() == []
    for config in (config_type(), config_type(value=None), config_type(value=value)):
        assert config.value == dt.time(13, 30, 45, 123456)
        assert config.get_load_diagnostics() == []
    fragment = yaml.safe_load(dump_yaml(config_type.blueprint_fragment()))
    assert fragment["value"] == {"default": "13:30:45.123456", "selector": {"time": {}}}
    assert config_type(value="00:00:00").value == dt.time(0)


@pytest.mark.reviewed(False)
@pytest.mark.parametrize("value", [True, 1, [], {}, "bad", "12:60:00", "25:00:00"])
def test_invalid_time_values_accumulate_without_default_fallback(value):
    config_type = bind(Time(default="01:00:00", allow_none=True))
    loaded = config_type(value=value)
    assert loaded.value is MISSING
    assert loaded.later == dt.time(0)
    diagnostics = loaded.get_load_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert diagnostics[0].context == ".value"
    diag = Diagnostics()
    with diag.child("value"):
        assert config_type.value.convert(value, diag) is MISSING
    assert diag.has_error
    assert diag.diagnostics == diagnostics


@pytest.mark.reviewed(False)
@pytest.mark.parametrize("value", [None, False, 1, [], "", "25:00:00"])
def test_invalid_time_defaults_are_build_errors(value):
    config_type = bind(Time(default=value))
    diagnostics = config_type.get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert config_type.value.default is MISSING
    assert "default" not in config_type.blueprint_fragment()["value"]


@pytest.mark.reviewed(False)
def test_missing_required_time_and_optional_none():
    required = bind(Time())
    for config in (required(), required(value=None)):
        assert config.value is MISSING
        assert config.later == dt.time(0)
        assert len(config.get_load_diagnostics()) == 1
    optional = bind(Time(allow_none=True))
    assert optional().value is None
    assert optional(value=None).get_load_diagnostics() == []


@pytest.mark.reviewed(False)
def test_time_constructor_arguments_and_section():
    class Config(BlueprintConfig):
        blueprint_name = "Time section"
        options = InputSection(collapsed=True)
        value = Time("unexpected", typo=True, section=options, default="00:00:00")

    diagnostics = Config.get_build_diagnostics()
    assert len(diagnostics) == 2
    assert all(
        d.severity.name == "ERROR" and d.context == ".value" for d in diagnostics
    )
    assert "positional argument" in diagnostics[0].message
    assert "typo" in diagnostics[1].message
    assert Config().value == dt.time(0)
    assert (
        Config.blueprint_fragment()["options"]["input"]["value"]["default"]
        == "00:00:00"
    )
    assert get_type_hints(Time.__init__)["section"] == InputSection | None
    assert (
        inspect.signature(Time).parameters["default"].kind
        is inspect.Parameter.KEYWORD_ONLY
    )


@pytest.mark.reviewed(False)
def test_time_offset_is_preserved_without_inference():
    expected = dt.time(13, 30, tzinfo=dt.timezone(dt.timedelta(hours=-7)))
    config_type = bind(Time(default=expected))
    assert config_type().value == expected
    assert config_type(value="13:30:00-07:00").value == expected
    assert config_type(value="13:30:00").value.tzinfo is None
