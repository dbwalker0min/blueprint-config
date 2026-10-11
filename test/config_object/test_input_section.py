from inline_snapshot import snapshot

from blueprint_config import BlueprintConfig, Boolean, InputSection


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
