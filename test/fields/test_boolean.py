from blueprint_config.fields import Boolean, BlueprintContext
from blueprint_config.diagnostic import Diagnostics

def test_simple_boolean_field():
    b = Boolean()

    d = Diagnostics()
    b.validate("test_field", diag=d)
    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {"selector": {"boolean": {}}}

def test_name_given_boolean_field():
    b = Boolean(name="My boolean")

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean"
    }

def test_name_given_description_field():
    b = Boolean(
        name="My boolean", 
        description="""\
        This is a boolean field
        This is the second line of the description""")

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "description": 'This is a boolean field\nThis is the second line of the description'
    }

def test_description_single_line():
    b = Boolean(
        name="My boolean", 
        description="This is a boolean field")

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "description": 'This is a boolean field'
    }

def test_description_multiline_first_line_inline():
    b = Boolean(
        name="My boolean", 
        description="""This is a boolean field
        This is the second line of the description""")

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "description": 'This is a boolean field\nThis is the second line of the description'
    }

def test_description_blank_lines():
    b = Boolean(
        name="My boolean", 
        description="""This is a boolean field

        This is the second line of the description""")

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "description": 'This is a boolean field\n\nThis is the second line of the description'
    }

def test_description_blank():
    b = Boolean(
        name="My boolean", 
        description="""\
        """)

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean"
    }

def test_description_nonstring():
    b = Boolean(
        name="My boolean", 
        description=12345)

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert diagnostics[0].message == "From field 'test_field': Type check failed for parameter 'description' of field 'test_field': expected type str, got type int"

def test_default_missing():
    b = Boolean(
        name="My boolean")

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean"
    }

def test_default_true():
    b = Boolean(
        name="My boolean",
        default=True)

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "default": True
    }

def test_default_false():
    b = Boolean(
        name="My boolean",
        default=False)

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "default": False
    }

def test_default_nonboolean():
    b = Boolean(
        name="My boolean",
        default=12345)  # ty:ignore[invalid-argument-type]

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert diagnostics[0].message == "From field 'test_field': Type check failed for parameter 'default' of field 'test_field': expected type bool, got type int"