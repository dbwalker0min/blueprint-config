import inspect
from typing import get_type_hints

import pytest
import yaml

from blueprint_config import (
    BlueprintConfig,
    Boolean,
    Diagnostics,
    InputSection,
    Number,
    dump_yaml,
)


def bind(field):
    class Config(BlueprintConfig):
        blueprint_name = "Number example"
        level = field

    return Config


@pytest.mark.parametrize("value", [0, -2, 4, 0.25])
def test_numeric_values_are_converted_to_float(value):
    config_type = bind(Number())
    config = config_type(level=value)
    assert config.level == float(value)
    assert type(config.level) is float
    assert config.get_load_diagnostics() == []
    assert config_type.get_build_diagnostics() == []


def test_zero_default_and_explicit_zero():
    zero = bind(Number(default=0, allow_none=True))
    assert zero().level == 0.0
    assert zero(level=None).level == 0.0
    assert bind(Number(default=10))(level=0).level == 0.0
    assert zero.blueprint_fragment()["level"]["default"] == 0


def test_optional_and_required_values():
    optional = bind(Number(allow_none=True))
    assert optional().level is None
    assert optional(level=None).level is None
    required = bind(Number())
    assert required().get_load_diagnostics()[0].context == ".level"
    diag = Diagnostics()
    with pytest.raises(ValueError, match="no default"):
        required.level.convert(None, diag)
    assert diag.has_error


@pytest.mark.parametrize("value", [True, False, "42", [], {}])
def test_reject_non_numeric_values_including_bool(value):
    with pytest.raises(TypeError, match="not numeric"):
        bind(Number())(level=value)


def test_selector_options_survive_yaml_serialization():
    config_type = bind(
        Number(
            name="Level",
            default=0,
            min=0,
            max=100.5,
            step=0.5,
            unit_of_measurement="%",
            mode="slider",
        )
    )
    assert config_type.get_build_diagnostics() == []
    fragment = yaml.safe_load(dump_yaml(config_type.blueprint_fragment()))
    assert fragment == {
        "level": {
            "name": "Level",
            "default": 0,
            "selector": {
                "number": {
                    "min": 0,
                    "max": 100.5,
                    "step": 0.5,
                    "unit_of_measurement": "%",
                    "mode": "slider",
                }
            },
        }
    }


def test_omitted_options_are_not_serialized():
    assert bind(Number()).blueprint_fragment() == {
        "level": {"selector": {"number": {}}}
    }


def test_any_step_and_box_mode():
    config_type = bind(Number(step="any", mode="box"))
    assert config_type.get_build_diagnostics() == []
    assert config_type.level.selector() == {"number": {"step": "any", "mode": "box"}}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"default": True},
        {"min": False},
        {"max": "100"},
        {"default": None},
        {"step": "small"},
        {"step": 0},
        {"step": -1},
        {"step": 0.000999},
        {"step": True},
        {"mode": "dial"},
        {"unit_of_measurement": 1},
    ],
)
def test_bad_declaration_values_produce_diagnostics(kwargs):
    diagnostics = bind(Number(**kwargs)).get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"


def test_section_association_for_typed_selectors():
    class Config(BlueprintConfig):
        blueprint_name = "Sections"
        options = InputSection(name="Options")
        enabled = Boolean(section=options)
        level = Number(section=options)

    assert Config.get_build_diagnostics() == []
    assert Config.enabled.section is Config.options
    assert Config.level.section is Config.options


def test_number_rejects_unknown_and_positional_arguments():
    with pytest.raises(TypeError, match="unexpected keyword"):
        Number(maximum=100)
    with pytest.raises(TypeError):
        Number(0, 100)


@pytest.mark.parametrize("selector", [Boolean, Number])
def test_public_constructor_has_resolvable_keyword_annotations(selector):
    # Editor-facing contract: no catch-all keywords hiding supported parameters.
    signature = inspect.signature(selector)
    hints = get_type_hints(selector.__init__)
    for name, parameter in signature.parameters.items():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert name in hints


@pytest.mark.parametrize("bounds", [{}, {"min": 0}, {"max": 10}])
def test_slider_requires_both_bounds(bounds):
    diagnostics = bind(Number(mode="slider", **bounds)).get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert "min and max are required" in diagnostics[0].message


@pytest.mark.parametrize("bounds", [{}, {"min": 0}, {"max": 10}, {"min": 0, "max": 10}])
@pytest.mark.parametrize("mode", [None, "box"])
def test_box_and_implicit_mode_allow_optional_bounds(bounds, mode):
    options = bounds | ({} if mode is None else {"mode": mode})
    config_type = bind(Number(**options))
    assert config_type.get_build_diagnostics() == []
    assert config_type.level.selector() == {"number": options}


@pytest.mark.parametrize("mode", ["box", "slider"])
def test_reversed_bounds_are_declaration_errors(mode):
    diagnostics = bind(Number(min=1, max=0, mode=mode)).get_build_diagnostics()
    assert len(diagnostics) == 1
    assert "min must not exceed max" in diagnostics[0].message


@pytest.mark.parametrize("mode", ["box", "slider"])
def test_equal_bounds_allow_the_single_value(mode):
    config_type = bind(Number(min=0, max=0, default=0, mode=mode))
    assert config_type.get_build_diagnostics() == []
    assert config_type().level == 0.0
    assert config_type(level=0).level == 0.0


@pytest.mark.parametrize("bounds,value", [({"min": 0}, -0.001), ({"max": 0}, 0.001)])
@pytest.mark.parametrize("allow_none", [False, True])
def test_out_of_range_defaults_are_declaration_errors(bounds, value, allow_none):
    config_type = bind(Number(default=value, allow_none=allow_none, **bounds))
    diagnostics = config_type.get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert "default value" in diagnostics[0].message
    # Conversion must also check a default selected by None resolution.
    diag = Diagnostics()
    with pytest.raises(ValueError):
        config_type.level.convert(None, diag)
    assert diag.has_error
    with pytest.raises(ValueError):
        config_type()


@pytest.mark.parametrize("mode", ["box", "slider"])
@pytest.mark.parametrize("value", [-2, 0, 2])
def test_bounds_are_inclusive_for_defaults_and_values(mode, value):
    config_type = bind(Number(min=-2, max=2, default=value, mode=mode))
    assert config_type.get_build_diagnostics() == []
    assert config_type().level == float(value)
    assert config_type(level=value).level == float(value)
    assert config_type(level=None).level == float(value)


@pytest.mark.parametrize(
    "bounds,value,message",
    [
        ({"min": 0}, -0.001, "below min"),
        ({"max": 0}, 0.001, "above max"),
        ({"min": -1, "max": 1, "mode": "slider"}, 1.001, "above max"),
    ],
)
def test_out_of_range_values_raise_and_record_diagnostics(bounds, value, message):
    config_type = bind(Number(default=0, allow_none=True, **bounds))
    diag = Diagnostics()
    with diag.child("level"), pytest.raises(ValueError, match=message):
        config_type.level.convert(value, diag)
    assert len(diag.diagnostics) == 1
    assert diag.has_error
    assert diag.diagnostics[0].context == ".level"
    with pytest.raises(ValueError, match=message):
        config_type(level=value)


@pytest.mark.parametrize("step", [0.001, 0.1, 2, "any"])
def test_step_does_not_round_or_restrict_value_multiples(step):
    config_type = bind(Number(min=0, max=10, step=step, default=0.12345))
    assert config_type.get_build_diagnostics() == []
    assert config_type().level == 0.12345
    assert config_type(level=1.23456).level == 1.23456
    assert (
        yaml.safe_load(dump_yaml(config_type.level.selector()))["number"]["step"]
        == step
    )


def test_bounded_optional_number_preserves_none_without_default():
    config_type = bind(Number(min=0, max=1, allow_none=True))
    assert config_type().level is None
    assert config_type(level=None).level is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"min": "zero", "max": 1, "default": 0},
        {"min": 0, "max": "one", "default": 0},
        {"min": 0, "max": 1, "default": "zero"},
    ],
)
def test_range_checks_do_not_crash_on_invalid_declaration_types(kwargs):
    diagnostics = bind(Number(**kwargs)).get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
