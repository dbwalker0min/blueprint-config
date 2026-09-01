from pprint import pprint

from blueprint_config import BlueprintConfig, Boolean, InputSection


def test_input_section():
    class MyInputSection(BlueprintConfig):
        blueprint_name = "my_input_section"

        input_section = InputSection(name='Options')

        check = Boolean(name="Check", section=input_section)

    bp = MyInputSection.build_blueprint()
    print(bp)
    assert False
