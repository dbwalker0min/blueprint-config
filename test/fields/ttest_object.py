from pprint import pprint

import yaml
from inline_snapshot import snapshot

from blueprint_config.diagnostic import Diagnostics
from blueprint_config.fields import Boolean, Object


def test_simple_object_field_no_object_type():
    obj = Object()

    d = Diagnostics()
    obj.validate("test_field", diag=d, valid_properties=[])
    diagnostics = d.diagnostics
    print(diagnostics)
    assert len(diagnostics) == 1
    assert diagnostics[0].message == snapshot(
        "From field 'test_field': 'object_type' must be a class derived from 'ConfigObject'. Is missing"
    )

if 0:
    def test_simple_object_field_with_object_type():
        class MyConfig(EmbeddedObject):
            check = Boolean(name="Check")

        class MyBpObject(BlueprintObject):
            object = Object(
                name="Object",
                object_type=MyConfig,
                multiple=True,
                label_field="check",
                default={"object": [{"check": True}, {"check": False}]},
            )
            item2 = Boolean(name="Item #2")

        diag_myconfig = MyConfig.diagnostics().diagnostics
        diag_mybpobject = MyBpObject.diagnostics().diagnostics
        pprint(diag_myconfig)
        pprint(diag_mybpobject)
        assert len(diag_myconfig) == 0
        assert len(diag_mybpobject) == 0
        bp = MyBpObject.blueprint_fragment()
        print(yaml.dump(bp, sort_keys=False))
        assert bp == snapshot(
            {
                "object": {
                    "name": "Object",
                    "default": {"object": [{"check": True}, {"check": False}]},
                    "selector": {
                        "object": {
                            "fields": {
                                "check": {"label": "Check", "selector": {"boolean": {}}}
                            },
                            "multiple": True,
                            "label_field": "check",
                        }
                    },
                },
                "item2": {"name": "Item #2", "selector": {"boolean": {}}},
            }
        )
