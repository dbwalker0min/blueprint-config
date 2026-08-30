from inline_snapshot import snapshot

from blueprint_config import (
    BlueprintConfig,
    Boolean,
    DiagnosticMessage,
    DiagnosticSeverity,
)


def test_simple_config_object_empty():
    class MyConfig(BlueprintConfig):
        pass

    d = MyConfig.get_build_diagnostics()
    print(d)
    registry = BlueprintConfig.get_registry()
    assert MyConfig in registry.values()
    assert len(d) == 1
    assert d[0].message == snapshot(
        "No fields defined in the configuration object 'MyConfig'."
    )
    assert d[0].severity == snapshot(DiagnosticSeverity.ERROR)


def test_simple_bp_object_minimal():
    class MyBP(BlueprintConfig):
        check = Boolean(name="Check")

    assert len(MyBP.get_build_diagnostics()) == 0
    assert MyBP.blueprint_fragment() == snapshot(
        {"check": {"name": "Check", "selector": {"boolean": {}}}}
    )

    # now test loading it
    mybp = MyBP(check=True)
    assert isinstance(mybp, MyBP)
    assert mybp.check is True


def test_simple_bp_object_missing_value():
    class MyBP(BlueprintConfig):
        check = Boolean(name="Check")

    assert len(MyBP.get_build_diagnostics()) == 0
    assert MyBP.blueprint_fragment() == snapshot(
        {"check": {"name": "Check", "selector": {"boolean": {}}}}
    )

    # now test loading it
    mybp = MyBP()
    diagnostics = mybp.get_load_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].message == snapshot(
        "No value provided for field with no default value and 'allow_none' false"
    )
    assert diagnostics[0].context == snapshot(".check")
    assert diagnostics[0].severity == snapshot(DiagnosticSeverity.ERROR)


def test_simple_bp_object_missing_and_default():
    class MyBP(BlueprintConfig):
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
        {"check": {"name": "Check", "default": False, "selector": {"boolean": {}}}}
    )

def test_simple_bp_object_with_extra_parameter_load():
    class MyBP(BlueprintConfig):
        check = Boolean(name="Check")

    mybp = MyBP(check=True, extra=True)
    diagnostics = mybp.get_load_diagnostics()
    assert diagnostics == snapshot([])
