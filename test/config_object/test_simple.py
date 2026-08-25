from inline_snapshot import snapshot

from blueprint_config.diagnostic import Diagnostics
from blueprint_config.fields import BlueprintContext, ConfigObject


def test_simple_config_object():
    class MyConfig(ConfigObject):
        pass

    config = MyConfig()

    d = Diagnostics()
    x = [g[1] for g in ConfigObject._registry.keys()]
    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert config.blueprint_fragment(BlueprintContext.INPUT) == snapshot({})
