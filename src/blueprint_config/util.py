from typing import Any

import yaml

from .types import InputRef


class TestDumper(yaml.SafeDumper):
    pass


def represent_str(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar(
        "tag:yaml.org,2002:str",
        value,
        style=style,
    )


def represent_input_ref(dumper, data):
    """YAML representer for InputRef objects."""
    return dumper.represent_scalar("!input", str(data))


TestDumper.add_representer(str, represent_str)
TestDumper.add_representer(InputRef, represent_input_ref)


def dump_yaml(value: Any) -> str:
    return yaml.dump(
        value,
        Dumper=TestDumper,
        sort_keys=False,
    )
