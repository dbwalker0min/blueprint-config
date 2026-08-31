from pprint import pprint

import pytest
import yaml
from inline_snapshot import snapshot

from blueprint_config import (
    BlueprintConfig,
    Boolean,
    DiagnosticMessage,
    DiagnosticSeverity,
    InputRef,
)

# I need to teach the YAML dumper how to represent multi-line strings and InputRef objects
def str_presenter(dumper, data):
    """YAML representer for multi-line strings."""
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)

def represent_input_ref(dumper, data):
    """YAML representer for InputRef objects."""
    return dumper.represent_scalar("!input", str(data))

yaml.add_representer(str, str_presenter)
yaml.add_representer(InputRef, represent_input_ref)

