import pytest
import yaml

from blueprint_config import (
    MISSING,
    BlueprintConfig,
    Boolean,
    Diagnostics,
    EmbeddedObject,
    InputSection,
    dump_yaml,
)


def bind(field):
    class Config(BlueprintConfig):
        blueprint_name = "Boolean example"
        enabled = field

    return Config


@pytest.mark.parametrize("value", [True, False])
def test_boolean_value(value):
    config_type = bind(Boolean())
    config = config_type(enabled=value)
    assert config.enabled is value
    assert config.get_load_diagnostics() == []
    assert config_type.get_build_diagnostics() == []


@pytest.mark.parametrize("default", [True, False])
@pytest.mark.parametrize("allow_none", [True, False])
def test_default_applies_to_missing_or_none_but_not_explicit_value(default, allow_none):
    config_type = bind(Boolean(default=default, allow_none=allow_none))
    assert config_type().enabled is default
    assert config_type(enabled=None).enabled is default
    assert config_type(enabled=not default).enabled is not default
    assert config_type.blueprint_fragment()["enabled"]["default"] is default


def test_optional_and_required_values():
    config_type = bind(Boolean(allow_none=True))
    assert config_type().enabled is None
    assert config_type(enabled=None).enabled is None
    required = bind(Boolean())
    assert required().get_load_diagnostics()[0].context == ".enabled"
    diag = Diagnostics()
    with pytest.raises(ValueError, match="no default"):
        required.enabled.convert(None, diag)
    assert diag.has_error


@pytest.mark.parametrize("value", [0, 1, "false", [], {}])
def test_reject_nonboolean_runtime_values(value):
    config_type = bind(Boolean())
    with pytest.raises(TypeError, match="not boolean"):
        config_type(enabled=value)


def test_blueprint_metadata_and_description():
    config_type = bind(
        Boolean(
            name="Enabled",
            description="""First line
            Second line""",
            default=False,
        )
    )
    assert config_type.blueprint_fragment() == {
        "enabled": {
            "name": "Enabled",
            "description": "First line\nSecond line",
            "default": False,
            "selector": {"boolean": {}},
        }
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": 1},
        {"description": 2},
        {"default": 1},
        {"default": None},
        {"allow_none": "yes"},
        {"allow_none": 1},
        {"default": 0},
        {"default": "false"},
        {"section": "options"},
        {"section": False},
        {"section": InputSection},
    ],
)
def test_bad_declaration_values_produce_build_diagnostics(kwargs):
    config_type = bind(Boolean(**kwargs))
    diagnostics = config_type.get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"


def test_unknown_keyword_and_positional_argument_rejected():
    with pytest.raises(TypeError, match="unexpected keyword"):
        Boolean(defualt=True)
    with pytest.raises(TypeError):
        Boolean("Enabled")


def test_boolean_in_embedded_object():
    class Settings(EmbeddedObject):
        enabled = Boolean(name="Enabled", default=False)

    assert Settings.get_build_diagnostics() == []
    assert Settings().enabled is False
    assert Settings.blueprint_fragment() == {
        "enabled": {"label": "Enabled", "selector": {"boolean": {}}}
    }


@pytest.mark.parametrize(
    "kwargs", [{}, {"name": "", "description": "", "section": None}]
)
def test_omitted_and_empty_metadata_are_not_serialized(kwargs):
    config_type = bind(Boolean(**kwargs))
    assert config_type.get_build_diagnostics() == []
    assert yaml.safe_load(dump_yaml(config_type.blueprint_fragment())) == {
        "enabled": {"selector": {"boolean": {}}},
    }


@pytest.mark.parametrize("allow_none", [False, True])
def test_explicit_missing_default_is_equivalent_to_omission(allow_none):
    config_type = bind(Boolean(default=MISSING, allow_none=allow_none))
    omitted = bind(Boolean(allow_none=allow_none))
    assert config_type.get_build_diagnostics() == []
    assert config_type.blueprint_fragment() == omitted.blueprint_fragment()
    assert "default" not in config_type.blueprint_fragment()["enabled"]
    for loaded in (
        (config_type(), config_type(enabled=None)) if allow_none else (config_type(),)
    ):
        if allow_none:
            assert loaded.enabled is None
            assert loaded.get_load_diagnostics() == []
        else:
            diagnostics = loaded.get_load_diagnostics()
            assert len(diagnostics) == 1
            assert diagnostics[0].severity.name == "ERROR"
            assert diagnostics[0].context == ".enabled"
    if not allow_none:
        with pytest.raises(ValueError, match="no default"):
            config_type(enabled=None)


@pytest.mark.parametrize("default", [True, False])
def test_boolean_default_survives_yaml_serialization(default):
    config_type = bind(Boolean(default=default))
    fragment = yaml.safe_load(dump_yaml(config_type.blueprint_fragment()))
    assert fragment == {
        "enabled": {"default": default, "selector": {"boolean": {}}},
    }
    assert fragment["enabled"]["default"] is default


@pytest.mark.parametrize("allow_none", [False, True])
def test_invalid_explicit_value_does_not_fall_back_to_default(allow_none):
    config_type = bind(Boolean(default=True, allow_none=allow_none))
    with pytest.raises(TypeError, match="not boolean"):
        config_type(enabled="false")


def test_boolean_section_rendering_and_value_loading():
    class Config(BlueprintConfig):
        blueprint_name = "Boolean sections"
        options = InputSection(name="Options")
        enabled = Boolean(name="Enabled", default=False, section=options)
        standalone = Boolean(default=True)

    assert Config.get_build_diagnostics() == []
    assert yaml.safe_load(dump_yaml(Config.blueprint_fragment())) == {
        "options": {
            "name": "Options",
            "input": {
                "enabled": {
                    "name": "Enabled",
                    "default": False,
                    "selector": {"boolean": {}},
                },
            },
        },
        "standalone": {"default": True, "selector": {"boolean": {}}},
    }
    loaded = Config(enabled=True, standalone=False)
    assert loaded.enabled is True
    assert loaded.standalone is False
    assert loaded.get_load_diagnostics() == []


@pytest.mark.parametrize("value", [True, False, None])
def test_optional_boolean_in_embedded_object(value):
    class Settings(EmbeddedObject):
        enabled = Boolean(allow_none=True, section=None)

    assert Settings.get_build_diagnostics() == []
    loaded = Settings(enabled=value)
    assert loaded.enabled is value
    assert loaded.get_load_diagnostics() == []
    assert Settings.blueprint_fragment() == {
        "enabled": {"selector": {"boolean": {}}},
    }
