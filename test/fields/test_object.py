from inline_snapshot import snapshot

from blueprint_config.diagnostic import Diagnostics
from blueprint_config.fields import BlueprintContext, ConfigObject, Object


def test_simple_object_field_no_object_type():

    obj = Object()

    d = Diagnostics()
    obj.validate("test_field", diag=d)
    diagnostics = d.diagnostics
    print(diagnostics)
    assert len(diagnostics) == 1
    assert diagnostics[0].message == snapshot(
        "From field 'test_field': 'object_type' must be a class derived from 'ConfigObject'. Is of type '_Missing'"
    )


def test_simple_object_field_with_object_type():
    class MyConfig(ConfigObject):
        pass

    obj = Object(object_type=MyConfig)

    d = Diagnostics()
    obj.validate("test_field", diag=d)
    diagnostics = d.diagnostics
    print(diagnostics)
    assert len(diagnostics) == 0

    assert obj.blueprint_fragment(BlueprintContext.INPUT) == snapshot(
        {"selector": {"object": {"fields": {}}}}
    )
