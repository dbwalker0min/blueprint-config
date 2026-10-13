import pytest
import yaml
from inline_snapshot import snapshot

from blueprint_config import (
    MISSING,
    BlueprintConfig,
    Boolean,
    DiagnosticSeverity,
    EmbeddedObject,
    InputSection,
    Number,
    Object,
    dump_yaml,
)


def test_input_section():
    class MyInputSection(BlueprintConfig):
        blueprint_name = "my_input_section"

        input_section = InputSection(
            name="Options", icon="mdi:car", description="This is a test section"
        )

        check = Boolean(
            name="Check", section=input_section, description="test", default=True
        )

    bp = MyInputSection.build_blueprint()
    assert MyInputSection.get_build_diagnostics() == snapshot([])
    assert bp == snapshot("""\
blueprint:
  domain: script
  name: my_input_section
  input:
    input_section:
      name: Options
      description: This is a test section
      icon: mdi:car
      input:
        check:
          name: Check
          description: test
          default: true
          selector:
            boolean: {}
sequence:
  sequence:
  - variables:
      result:
        check: !input 'check'
  - stop: Return blueprint configuration
    response_variable: result
mode: single
""")


@pytest.mark.parametrize("section_first", [True, False])
def test_collapsed_section_reports_each_missing_default(section_first):
    section = InputSection(collapsed=True)
    declarations = {
        "required": Boolean(section=section),
        "optional": Boolean(section=section, allow_none=True),
        "missing": Boolean(section=section, default=MISSING),
        "valid": Boolean(section=section, default=False),
    }
    declarations = (
        {"options": section, **declarations}
        if section_first
        else {**declarations, "options": section}
    )
    config = type(
        "Config",
        (BlueprintConfig,),
        {
            "blueprint_name": "Collapsed inputs",
            **declarations,
        },
    )

    diagnostics = config.get_build_diagnostics()
    assert len(diagnostics) == 3
    assert all(d.severity == DiagnosticSeverity.ERROR for d in diagnostics)
    assert [d.message for d in diagnostics] == [
        f"Input {name!r} in collapsed section 'options' must have a default value"
        for name in ("required", "optional", "missing")
    ]


@pytest.mark.parametrize("options", [{}, {"collapsed": False}])
def test_expanded_section_does_not_require_defaults(options):
    class Config(BlueprintConfig):
        blueprint_name = "Expanded inputs"
        section = InputSection(**options)
        required = Boolean(section=section)

    assert Config.get_build_diagnostics() == []


def test_collapsed_section_accepts_false_zero_and_empty_defaults():
    class Schema(EmbeddedObject):
        enabled = Boolean(default=False)

    class Config(BlueprintConfig):
        blueprint_name = "Collapsed defaults"
        section = InputSection(collapsed=True)
        disabled = Boolean(section=section, default=False)
        zero = Number(section=section, default=0)
        empty_mapping = Object(section=section, object_type=Schema, default={})
        empty_list = Object(
            section=section, object_type=Schema, multiple=True, default=[]
        )
        ungrouped = Boolean()
        other_section = InputSection()
        other_input = Boolean(section=other_section)

    assert Config.get_build_diagnostics() == []
    inputs = Config.blueprint_fragment()["section"]["input"]
    assert inputs["disabled"]["default"] is False
    assert inputs["zero"]["default"] == 0
    assert inputs["empty_mapping"]["default"] == {}
    assert inputs["empty_list"]["default"] == []


def test_empty_collapsed_section_has_no_missing_defaults():
    class Config(BlueprintConfig):
        blueprint_name = "Empty section"
        section = InputSection(collapsed=True)

    assert Config.get_build_diagnostics() == []


@pytest.mark.parametrize("collapsed", [False, True])
@pytest.mark.parametrize("parent_first", [False, True])
def test_nested_sections_produce_build_error(collapsed, parent_first):
    parent = InputSection()
    child = InputSection(section=parent, collapsed=collapsed)
    sections = (
        {"parent": parent, "child": child}
        if parent_first
        else {"child": child, "parent": parent}
    )
    config = type(
        "Config",
        (BlueprintConfig,),
        {
            "blueprint_name": "Nested sections",
            **sections,
            "enabled": Boolean(section=child, default=False),
        },
    )

    diagnostics = config.get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity == DiagnosticSeverity.ERROR
    assert diagnostics[0].message == (
        "Input section 'child' cannot be nested in another section"
    )


def test_nesting_error_does_not_hide_missing_default_error_or_custom_validation():
    class Config(BlueprintConfig):
        blueprint_name = "Invalid nesting and defaults"
        parent = InputSection()
        child = InputSection(section=parent, collapsed=True)
        required = Boolean(section=child)

        @classmethod
        def validate_config(cls, diag):
            diag.warning("Custom validation ran")

    diagnostics = Config.get_build_diagnostics()
    assert [(d.severity, d.message) for d in diagnostics] == [
        (
            DiagnosticSeverity.ERROR,
            "Input section 'child' cannot be nested in another section",
        ),
        (
            DiagnosticSeverity.ERROR,
            "Input 'required' in collapsed section 'child' must have a default value",
        ),
        (DiagnosticSeverity.WARNING, "Custom validation ran"),
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": None},
        {"name": 1},
        {"description": False},
        {"description": []},
        {"icon": None},
        {"icon": 1},
        {"collapsed": None},
        {"collapsed": 0},
        {"collapsed": 1},
        {"collapsed": "true"},
        {"section": "parent"},
        {"section": InputSection},
    ],
)
def test_invalid_section_arguments_produce_build_errors(kwargs):
    class Config(BlueprintConfig):
        blueprint_name = "Invalid section argument"
        options = InputSection(**kwargs)

    diagnostics = Config.get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity == DiagnosticSeverity.ERROR
    assert "From field 'options'" in diagnostics[0].message
    assert "Expected type" in diagnostics[0].message


def test_unknown_section_argument_is_reported_and_omitted():
    class Config(BlueprintConfig):
        blueprint_name = "Unknown section argument"
        options = InputSection(typo=True)

    diagnostics = Config.get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity == DiagnosticSeverity.WARNING
    assert "Unused field argument: typo=True" in diagnostics[0].message
    assert Config.blueprint_fragment() == {"options": {"input": {}}}


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"name": "", "description": "", "icon": "", "collapsed": False}],
)
def test_empty_section_omits_empty_metadata(kwargs):
    class Config(BlueprintConfig):
        blueprint_name = "Empty metadata"
        options = InputSection(**kwargs)

    assert Config.get_build_diagnostics() == []
    assert Config.blueprint_fragment() == {"options": {"input": {}}}


def test_section_metadata_and_collapsed_flag_survive_yaml_serialization():
    class Config(BlueprintConfig):
        blueprint_name = "Section metadata"
        options = InputSection(
            name="Advanced",
            description="""
                **Advanced options**
                Choose carefully.
            """,
            icon="mdi:cog",
            collapsed=True,
        )
        enabled = Boolean(section=options, default=False)

    assert Config.get_build_diagnostics() == []
    assert yaml.safe_load(dump_yaml(Config.blueprint_fragment())) == {
        "options": {
            "name": "Advanced",
            "description": "**Advanced options**\nChoose carefully.",
            "icon": "mdi:cog",
            "collapsed": True,
            "input": {"enabled": {"default": False, "selector": {"boolean": {}}}},
        }
    }


def test_multiple_sections_keep_members_separate_ordered_and_values_flat():
    class Config(BlueprintConfig):
        blueprint_name = "Multiple sections"
        first = InputSection(name="Options")
        second = InputSection(name="Options")
        standalone = Boolean(default=True)
        first_a = Boolean(section=first, default=False)
        second_a = Number(section=second, default=0)
        first_b = Boolean(section=first, default=True)
        second_b = Boolean(section=second, default=False)

    assert Config.get_build_diagnostics() == []
    fragment = Config.blueprint_fragment()
    assert list(fragment) == ["first", "second", "standalone"]
    assert list(fragment["first"]["input"]) == ["first_a", "first_b"]
    assert list(fragment["second"]["input"]) == ["second_a", "second_b"]
    assert "selector" not in fragment["first"]
    assert "selector" not in fragment["second"]
    assert list(Config.field_items()) == [
        "standalone",
        "first_a",
        "second_a",
        "first_b",
        "second_b",
    ]
    loaded = Config(first_a=True, second_a=5)
    assert loaded.get_load_diagnostics() == []
    assert loaded.first_a is True
    assert loaded.second_a == 5.0
    assert loaded.standalone is True
    assert loaded.first_b is True
    assert loaded.second_b is False
    sequence = Config.build_blueprint()
    for name in Config.field_items():
        assert sequence.count(f"!input '{name}'") == 1
    assert "!input 'first'" not in sequence
    assert "!input 'second'" not in sequence


def test_input_section_import_paths_preserve_class_identity():
    from blueprint_config.config import InputSection as ConfigSection
    from blueprint_config.fields import InputSection as FieldsSection
    from blueprint_config.fields.input_section import InputSection as ModuleSection
    from blueprint_config.items import InputSection as ItemsSection

    assert (
        InputSection is ConfigSection is FieldsSection is ModuleSection is ItemsSection
    )
