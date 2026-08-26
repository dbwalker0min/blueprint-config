from inline_snapshot import snapshot

from blueprint_config.diagnostic import DiagnosticSeverity
from blueprint_config.fields import BlueprintObject, Boolean


def test_simple_config_object_empty():
    class MyConfig(BlueprintObject):
        pass

    d = MyConfig.diagnostics().diagnostics
    registry = BlueprintObject.get_registry()
    assert MyConfig in registry.values()
    assert len(d) == 1
    assert d[0].message == snapshot(
        "No fields defined in the configuration object 'MyConfig'."
    )
    assert d[0].severity == snapshot(DiagnosticSeverity.ERROR)


def test_simple_bp_object_minimal():
    class MyBP(BlueprintObject):
        check = Boolean(name="Check")

    assert len(MyBP.diagnostics().diagnostics) == 0
    assert MyBP.blueprint_fragment() == snapshot(
        {"check": {"name": "Check", "selector": {"boolean": {}}}}
    )

    # now test loading it
    mybp = MyBP(check=True)
    assert isinstance(mybp, MyBP)
    assert mybp.check is True


def test_simple_bp_object_missing_value():
    class MyBP(BlueprintObject):
        check = Boolean(name="Check")

    assert len(MyBP.diagnostics().diagnostics) == 0
    assert MyBP.blueprint_fragment() == snapshot(
        {"check": {"name": "Check", "selector": {"boolean": {}}}}
    )

    # now test loading it
    mybp = MyBP()
    diagnostics = mybp.get_load_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].message == snapshot(
        "From path 'root': No value provided for field with no default value and 'allow_none' false"
    )
    assert diagnostics[0].severity == snapshot(DiagnosticSeverity.ERROR)


def test_simple_bp_object_missing_and_default():
    class MyBP(BlueprintObject):
        check = Boolean(name="Check", default=True)

    assert len(MyBP.diagnostics().diagnostics) == 0
    assert MyBP.blueprint_fragment() == snapshot(
        {"check": {"name": "Check", "default": True, "selector": {"boolean": {}}}}
    )

    # now test loading it without providing the value
    mybp = MyBP()
    diagnostics = mybp.get_load_diagnostics()
    assert len(diagnostics) == 0
    assert mybp.check is True
