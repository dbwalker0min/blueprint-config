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
            translation_key="level",
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
                    "translation_key": "level",
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
        {"step": True},
        {"mode": "dial"},
        {"unit_of_measurement": 1},
        {"translation_key": 2},
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
