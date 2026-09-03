from blueprint_config import BlueprintConfig, Boolean, EmbeddedObject, Object


def test_simple_object_field_with_object_type():
    class MyConfig(EmbeddedObject):
        check = Boolean(name="Check")

    class MyBpObject(BlueprintConfig):
        blueprint_name = 'my_blueprint_object'

        object = Object(
            name="Object",
            object_type=MyConfig,
            multiple=True,
            label_field="check",
            default={"object": [{"check": True}, {"check": False}]},
        )
        item2 = Boolean(name="Item #2")

    build_diag_MyConfig = MyConfig.get_build_diagnostics()
    build_diag_MyBpObject = MyBpObject.get_build_diagnostics()
    print('MyConfig build diagnostics:')
    for d in build_diag_MyConfig:
        print(d)
    print('MyBpObject build diagnostics:')
    for d in build_diag_MyBpObject:
        print(d)
    assert len(build_diag_MyConfig) == 0
    assert len(build_diag_MyBpObject) == 0
