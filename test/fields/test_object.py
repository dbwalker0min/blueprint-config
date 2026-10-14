import pytest
import yaml

from blueprint_config import (
    MISSING,
    BlueprintConfig,
    Boolean,
    Diagnostics,
    EmbeddedObject,
    Object,
    dump_yaml,
)

pytestmark = pytest.mark.review_required


class MyConfig(EmbeddedObject):
    check = Boolean(name="Check")


def bind(field):
    class Config(BlueprintConfig):
        blueprint_name = "Object example"
        object = field
        sibling = Boolean(default=False)

    return Config


@pytest.mark.reviewed(False)
def test_simple_object_field_with_object_type():
    config_type = bind(
        Object(
            name="Object",
            object_type=MyConfig,
            multiple=True,
            label_field="check",
            description_field="check",
            default=[{"check": True}, {"check": False}],
        )
    )
    assert MyConfig.get_build_diagnostics() == []
    assert config_type.get_build_diagnostics() == []
    assert config_type.object._parent_class is config_type
    assert config_type.build_blueprint()
    fragment = yaml.safe_load(dump_yaml(config_type.blueprint_fragment()))
    assert fragment["object"] == {
        "name": "Object",
        "default": [{"check": True}, {"check": False}],
        "selector": {
            "object": {
                "fields": {"check": {"label": "Check", "selector": {"boolean": {}}}},
                "multiple": True,
                "label_field": "check",
                "description_field": "check",
            }
        },
    }
    loaded = config_type()
    assert all(type(item) is MyConfig for item in loaded.object)
    assert [item.check for item in loaded.object] == [True, False]
    assert loaded.get_load_diagnostics() == []
    assert config_type(object=[]).object == []


@pytest.mark.reviewed(False)
def test_single_object_conversion_and_default():
    config_type = bind(Object(object_type=MyConfig, default={"check": True}))
    assert config_type().object.check is True
    assert config_type(object=None).object.check is True
    value = config_type(object={"check": False}).object
    assert type(value) is MyConfig
    assert value.check is False
    assert config_type.object.selector() == {
        "object": {
            "fields": {"check": {"label": "Check", "selector": {"boolean": {}}}},
        }
    }


@pytest.mark.reviewed(False)
def test_nested_embedded_objects():
    class Outer(EmbeddedObject):
        inner = Object(object_type=MyConfig)

    config_type = bind(Object(object_type=Outer))
    assert Outer.get_build_diagnostics() == []
    assert config_type.build_blueprint()
    fields = config_type.object.selector()["object"]["fields"]
    assert fields["inner"]["selector"] == Outer.inner.selector()
    value = config_type(object={"inner": {"check": False}}).object
    assert type(value) is Outer
    assert type(value.inner) is MyConfig
    assert value.inner.check is False


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"object_type": None},
        {"object_type": 42},
        {"object_type": dict},
        {"object_type": BlueprintConfig},
    ],
)
@pytest.mark.reviewed(False)
def test_invalid_object_type_has_build_and_load_diagnostics(kwargs):
    config_type = bind(Object(**kwargs))
    diagnostics = config_type.get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert "object_type" in diagnostics[0].message
    assert config_type.object.selector() == {"object": {"fields": {}}}
    assert config_type.build_blueprint()
    loaded = config_type(object={})
    assert loaded.object is MISSING
    assert loaded.sibling is False
    diagnostics = loaded.get_load_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].context == ".object"
    assert "EmbeddedObject" in diagnostics[0].message


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.reviewed(False)
def test_optional_and_required_objects(multiple):
    optional = bind(Object(object_type=MyConfig, allow_none=True, multiple=multiple))
    assert optional().object == ([] if multiple else None)
    required = bind(Object(object_type=MyConfig, multiple=multiple))
    diag = Diagnostics()
    assert required.object.convert(None, diag) is MISSING
    assert diag.has_error
    assert len(diag.diagnostics) == 1


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.parametrize("explicit_none", [False, True])
@pytest.mark.reviewed(False)
def test_default_precedes_allow_none(multiple, explicit_none):
    default = [{"check": False}] if multiple else {"check": False}
    config_type = bind(
        Object(
            object_type=MyConfig, multiple=multiple, default=default, allow_none=True
        )
    )
    loaded = config_type(object=None) if explicit_none else config_type()
    values = loaded.object if multiple else [loaded.object]
    assert len(values) == 1
    assert type(values[0]) is MyConfig
    assert values[0].check is False
    assert loaded.get_load_diagnostics() == []


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.reviewed(False)
def test_explicit_values_override_defaults_without_mutating_input(multiple):
    from copy import deepcopy

    default = [{"check": True}] if multiple else {"check": True}
    supplied = [{"check": False}] if multiple else {"check": False}
    original = deepcopy(supplied)
    config_type = bind(Object(object_type=MyConfig, multiple=multiple, default=default))
    loaded = config_type(object=supplied)
    values = loaded.object if multiple else [loaded.object]
    assert values[0].check is False
    values[0].check = True
    assert supplied == original
    assert default == ([{"check": True}] if multiple else {"check": True})


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.reviewed(False)
def test_defaults_create_independent_instances(multiple):
    default = [{"check": False}] if multiple else {"check": False}
    config_type = bind(Object(object_type=MyConfig, multiple=multiple, default=default))
    first, second = config_type(), config_type()
    first_value = first.object[0] if multiple else first.object
    second_value = second.object[0] if multiple else second.object
    first_value.check = True
    assert second_value.check is False
    if multiple:
        first.object.append(MyConfig(check=True))
        assert len(second.object) == 1
    assert config_type.blueprint_fragment()["object"]["default"] == default
    assert default == ([{"check": False}] if multiple else {"check": False})


@pytest.mark.reviewed(False)
def test_empty_mapping_uses_embedded_defaults_instead_of_object_default():
    class WithDefault(EmbeddedObject):
        check = Boolean(default=False)

    config_type = bind(Object(object_type=WithDefault, default={"check": True}))
    assert config_type(object={}).object.check is False
    assert config_type().object.check is True


@pytest.mark.reviewed(False)
def test_empty_list_default_is_preserved():
    config_type = bind(Object(object_type=MyConfig, multiple=True, default=[]))
    assert config_type().object == []
    assert config_type(object=None).object == []
    assert config_type.blueprint_fragment()["object"]["default"] == []
    assert config_type.get_build_diagnostics() == []


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.reviewed(False)
def test_missing_required_object_records_field_context(multiple):
    loaded = bind(Object(object_type=MyConfig, multiple=multiple))()
    diagnostics = loaded.get_load_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert diagnostics[0].context == ".object"
    assert "No value provided" in diagnostics[0].message


@pytest.mark.parametrize(
    "kwargs",
    [
        {"multiple": "true"},
        {"multiple": 1},
        {"label_field": True},
        {"description_field": 42},
        {"allow_none": "yes"},
        {"default": None},
        {"default": False},
        {"default": "invalid"},
    ],
)
@pytest.mark.reviewed(False)
def test_invalid_option_types_report_build_errors(kwargs):
    config_type = bind(Object(object_type=MyConfig, **kwargs))
    diagnostics = config_type.get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert "Expected type" in diagnostics[0].message


@pytest.mark.reviewed(False)
def test_unknown_and_positional_options_report_build_errors():
    config_type = bind(Object("unexpected", object_type=MyConfig, unknown_option=True))
    diagnostics = config_type.get_build_diagnostics()
    assert len(diagnostics) == 2
    assert all(
        d.severity.name == "ERROR" and d.context == ".object" for d in diagnostics
    )
    assert "positional argument" in diagnostics[0].message
    assert "unknown_option" in diagnostics[1].message


@pytest.mark.parametrize("option", ["label_field", "description_field"])
@pytest.mark.reviewed(False)
def test_label_and_description_options_are_independent(option):
    config_type = bind(Object(object_type=MyConfig, **{option: "check"}))
    selector = yaml.safe_load(dump_yaml(config_type.object.selector()))["object"]
    assert selector == {
        "fields": {"check": {"label": "Check", "selector": {"boolean": {}}}},
        option: "check",
    }


@pytest.mark.reviewed(False)
def test_explicit_empty_options_are_omitted():
    field = bind(
        Object(
            object_type=MyConfig, multiple=False, label_field="", description_field=""
        )
    ).object
    assert set(field.selector()["object"]) == {"fields"}


@pytest.mark.parametrize("value", [False, 42, "invalid", [True]])
@pytest.mark.reviewed(False)
def test_single_object_rejects_non_mapping_values(value):
    loaded = bind(Object(object_type=MyConfig))(object=value)
    assert loaded.object is MISSING
    assert loaded.sibling is False
    assert len(loaded.get_load_diagnostics()) == 1
    assert loaded.get_load_diagnostics()[0].context == ".object"


@pytest.mark.parametrize("value", [[None], [False], [42], ["invalid"]])
@pytest.mark.reviewed(False)
def test_multiple_objects_reject_non_mapping_elements(value):
    loaded = bind(Object(object_type=MyConfig, multiple=True))(object=value)
    assert loaded.object == [MISSING]
    assert loaded.sibling is False
    assert len(loaded.get_load_diagnostics()) == 1
    assert loaded.get_load_diagnostics()[0].context == ".object[0]"


@pytest.mark.reviewed(False)
def test_embedded_field_conversion_errors_reach_parent_diagnostics():
    loaded = bind(Object(object_type=MyConfig))(object={"check": "invalid"})
    assert loaded.object.check is MISSING
    assert loaded.sibling is False
    assert len(loaded.get_load_diagnostics()) == 1
    assert loaded.get_load_diagnostics()[0].context == ".object.check"
    assert "Boolean" in loaded.get_load_diagnostics()[0].message


@pytest.mark.reviewed(False)
def test_repeated_nested_objects_keep_order_and_types():
    class Group(EmbeddedObject):
        children = Object(object_type=MyConfig, multiple=True)

    config_type = bind(Object(object_type=Group, multiple=True))
    loaded = config_type(
        object=[
            {"children": [{"check": False}, {"check": True}]},
            {"children": []},
        ]
    )
    assert all(type(group) is Group for group in loaded.object)
    assert all(type(child) is MyConfig for child in loaded.object[0].children)
    assert [child.check for child in loaded.object[0].children] == [False, True]
    assert loaded.object[1].children == []
    fields = config_type.object.selector()["object"]["fields"]
    assert fields["children"]["selector"]["object"]["multiple"] is True
    assert set(fields["children"]["selector"]["object"]["fields"]) == {"check"}


@pytest.mark.reviewed(False)
def test_object_in_input_section_renders_embedded_fields():
    from blueprint_config import InputSection

    class Config(BlueprintConfig):
        blueprint_name = "Section example"
        options = InputSection(name="Options")
        item = Object(
            object_type=MyConfig,
            section=options,
            name="Item",
            description="Choose values",
        )

    assert Config.get_build_diagnostics() == []
    fragment = Config.blueprint_fragment()
    assert set(fragment) == {"options"}
    assert fragment["options"]["input"]["item"] == {
        "name": "Item",
        "description": "Choose values",
        "selector": {
            "object": {
                "fields": {
                    "check": {"label": "Check", "selector": {"boolean": {}}},
                }
            }
        },
    }
    assert Config(item={"check": False}).item.check is False


@pytest.mark.reviewed(False)
@pytest.mark.parametrize("value", [False, 42, "invalid", {}, ({},)])
def test_multiple_object_requires_list_without_falling_back_to_default(value):
    config_type = bind(Object(object_type=MyConfig, multiple=True, default=[]))
    loaded = config_type(object=value)
    assert loaded.object is MISSING
    assert loaded.sibling is False
    assert len(loaded.get_load_diagnostics()) == 1
    assert loaded.get_load_diagnostics()[0].context == ".object"
    assert "list of mappings" in loaded.get_load_diagnostics()[0].message


@pytest.mark.reviewed(False)
@pytest.mark.parametrize("multiple", [False, True])
def test_object_rejects_non_string_mapping_keys(multiple):
    value = {1: False}
    loaded = bind(Object(object_type=MyConfig, multiple=multiple))(
        object=[value] if multiple else value
    )
    assert loaded.object == [MISSING] if multiple else loaded.object is MISSING
    assert len(loaded.get_load_diagnostics()) == 1
    assert loaded.get_load_diagnostics()[0].context == (
        ".object[0]" if multiple else ".object"
    )


@pytest.mark.reviewed(False)
@pytest.mark.parametrize(
    "multiple,default,contexts",
    [
        (False, [], [".object.default"]),
        (True, {}, [".object.default"]),
        (False, {"check": "bad"}, [".object.default.check"]),
        (
            True,
            [False, {"check": "bad"}],
            [".object.default[0]", ".object.default[1].check"],
        ),
    ],
)
def test_invalid_object_defaults_accumulate_build_errors(multiple, default, contexts):
    config_type = bind(Object(object_type=MyConfig, multiple=multiple, default=default))
    diagnostics = config_type.get_build_diagnostics()
    assert [d.context for d in diagnostics] == contexts
    assert all(d.severity.name == "ERROR" for d in diagnostics)
    assert config_type.object.default is MISSING
    assert "default" not in config_type.blueprint_fragment()["object"]
    # An explicit valid value still loads even when the declaration default was bad.
    valid = {"check": False}
    loaded = config_type(object=[valid] if multiple else valid)
    assert loaded.get_load_diagnostics() == []
