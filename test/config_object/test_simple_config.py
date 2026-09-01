import pytest
from inline_snapshot import snapshot

from blueprint_config import (
    BlueprintConfig,
    Boolean,
    DiagnosticMessage,
    DiagnosticSeverity,
)


def test_simple_config_object_empty():
    class MyConfig(BlueprintConfig):
        blueprint_name = "MyConfig"

    d = MyConfig.get_build_diagnostics()
    print(d)
    registry = BlueprintConfig.get_registry()
    assert MyConfig in registry.values()
    assert len(d) == 1
    assert d[0].message == snapshot(
        "No fields defined in the configuration object 'MyConfig'."
    )
    assert d[0].severity == snapshot(DiagnosticSeverity.ERROR)


def test_simple_config_object_with_no_blueprint_name():

    with pytest.raises(ValueError):

        class MyConfig(BlueprintConfig):
            pass


def test_simple_config_object_with_invalid_type_blueprint_name():
    with pytest.raises(TypeError):

        class MyConfig(BlueprintConfig):
            blueprint_name = 123


def test_simple_bp_object_minimal():
    class MyBP(BlueprintConfig):
        blueprint_name = "MyBP"

        check = Boolean(name="Check")

    assert len(MyBP.get_build_diagnostics()) == 0

    # It's easier to see in yaml
    assert MyBP.build_blueprint() == snapshot("""\
blueprint:
  domain: script
  name: MyBP
  input:
    check:
      name: Check
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


def test_simple_bp_object_with_author_and_description():
    class MyBP(BlueprintConfig):
        blueprint_name = "MyBP"
        blueprint_author = "Author Name"
        blueprint_description = """
            <p>This is a multi-line
            description. It has a markdown list:

            - Item 1
            - Item 2
            - Item 3
            """
        check = Boolean(name="Check")

    assert len(MyBP.get_build_diagnostics()) == 0
    bp = MyBP.build_blueprint()
    assert bp == snapshot(
        """\
blueprint:
  domain: script
  name: MyBP
  description: |-
    <p>This is a multi-line
    description. It has a markdown list:

    - Item 1
    - Item 2
    - Item 3
  author: Author Name
  input:
    check:
      name: Check
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
"""
    )


def test_simple_bp_object_missing_value():
    class MyBP(BlueprintConfig):
        blueprint_name = "MyBP"
        check = Boolean(name="Check")

    assert len(MyBP.get_build_diagnostics()) == 0
    assert MyBP.blueprint_fragment() == snapshot(
        {"check": {"name": "Check", "selector": {"boolean": {}}}}
    )

    # now test loading it
    mybp = MyBP()
    diagnostics = mybp.get_load_diagnostics()
    print(diagnostics)
    assert len(diagnostics) == 1
    assert diagnostics[0].message == snapshot(
        "No value provided for field with no default value and 'allow_none' false"
    )
    assert diagnostics[0].context == snapshot(".check")
    assert diagnostics[0].severity == snapshot(DiagnosticSeverity.ERROR)


def test_simple_bp_object_missing_and_default():
    class MyBP(BlueprintConfig):
        blueprint_name = "MyBP"
        check = Boolean(name="Check", default=True)

    print(MyBP.get_build_diagnostics())
    assert len(MyBP.get_build_diagnostics()) == 0
    assert MyBP.blueprint_fragment() == snapshot(
        {"check": {"name": "Check", "default": True, "selector": {"boolean": {}}}}
    )

    # now test loading it without providing the value
    mybp = MyBP()
    diagnostics = mybp.get_load_diagnostics()
    assert len(diagnostics) == 0
    assert mybp.check is True


def test_simple_bp_object_with_extra_parameter():
    class MyBP(BlueprintConfig):
        blueprint_name = "MyBP"
        check = Boolean(name="Check", extra="asdf")

    print(MyBP.get_build_diagnostics())
    assert len(MyBP.get_build_diagnostics()) == 1
    assert MyBP.get_build_diagnostics() == snapshot(
        [
            DiagnosticMessage(
                severity=DiagnosticSeverity.WARNING,
                message="From field check: Unused field argument: extra=asdf",
            )
        ]
    )
    assert MyBP.get_build_diagnostics()[0].severity == snapshot(
        DiagnosticSeverity.WARNING
    )
    assert MyBP.blueprint_fragment() == snapshot(
        {"check": {"name": "Check", "selector": {"boolean": {}}}}
    )


def test_simple_bp_object_with_extra_parameter_load():
    class MyBP(BlueprintConfig):
        blueprint_name = "MyBP"
        check = Boolean(name="Check")

    mybp = MyBP(check=True, extra=True)
    diagnostics = mybp.get_load_diagnostics()
    assert diagnostics == snapshot(
        [
            DiagnosticMessage(
                severity=DiagnosticSeverity.WARNING,
                message="Unused field argument: extra=True",
            )
        ]
    )
