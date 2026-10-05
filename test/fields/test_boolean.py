import pytest

from blueprint_config import BlueprintConfig, Boolean, Diagnostics, EmbeddedObject


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
def test_default_applies_to_missing_or_none_but_not_explicit_value(default):
    config_type = bind(Boolean(default=default, allow_none=True))
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
