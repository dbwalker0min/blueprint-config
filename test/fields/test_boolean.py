import pytest
from inline_snapshot import snapshot

from blueprint_config.diagnostic import Diagnostics
from blueprint_config.fields import BlueprintContext, Boolean


def test_simple_boolean_field():
    b = Boolean()

    d = Diagnostics()
    b.validate("test_field", diag=d)
    diagnostics = d.diagnostics
    print(diagnostics)
    assert len(diagnostics) == 0
    # Testing that default is not emitted from blueprint fragment when it is MISSING
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {"selector": {"boolean": {}}}

    # Testing that the convert method works correctly for True and False
    assert b.convert(True) is True
    assert b.convert(False) is False

    # Testing that None with no default raises a ValueError
    with pytest.raises(ValueError) as excinfo:
        b.convert(None)
    assert str(excinfo.value) == snapshot('Boolean field has no default and no value was provided')


def test_name_given_boolean_field():
    b = Boolean(name="My boolean")

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
    }


def test_name_given_description_field():
    b = Boolean(
        name="My boolean",
        description="""\
        This is a boolean field
        This is the second line of the description""",
    )

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "description": "This is a boolean field\nThis is the second line of the description",
    }


def test_description_single_line():
    b = Boolean(name="My boolean", description="This is a boolean field")

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "description": "This is a boolean field",
    }


def test_description_multiline_first_line_inline():
    b = Boolean(
        name="My boolean",
        description="""This is a boolean field
        This is the second line of the description""",
    )

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "description": "This is a boolean field\nThis is the second line of the description",
    }


def test_description_blank_lines():
    b = Boolean(
        name="My boolean",
        description="""This is a boolean field

        This is the second line of the description""",
    )

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "description": "This is a boolean field\n\nThis is the second line of the description",
    }


def test_description_blank():
    b = Boolean(
        name="My boolean",
        description="""\
        """,
    )

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
    }


def test_description_nonstring():
    b = Boolean(name="My boolean", description=12345)

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert (
        diagnostics[0].message
        == "From field 'test_field': Type check failed for parameter 'description' of field 'test_field': expected type str, got type int"
    )


def test_default_missing():
    b = Boolean(name="My boolean")

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
    }


def test_default_true():
    b = Boolean(name="My boolean", default=True)

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    print(diagnostics)
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "default": True,
    }
    # Test convert method for True and False
    assert b.convert(True) is True
    assert b.convert(False) is False
    # Test convert method for None when default is provided
    assert b.convert(None) is True

    # Test convert for None with default
    assert b.convert(None) == True

def test_default_false():
    b = Boolean(name="My boolean", default=False)

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == {
        "selector": {"boolean": {}},
        "name": "My boolean",
        "default": False,
    }
    # Test convert method for True and False
    assert b.convert(True) is True
    assert b.convert(False) is False
    # Test convert method for None when default is provided
    assert b.convert(None) is False



def test_default_nonboolean():
    b = Boolean(name="My boolean", default=12345)  # ty:ignore[invalid-argument-type]

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"
    assert (
        diagnostics[0].message
        == "From field 'test_field': Type check failed for parameter 'default' of field 'test_field': expected type bool, got type int"
    )

def test_with_allow_none_true_and_default_none():
    b = Boolean(name="My boolean", allow_none=True)

    d = Diagnostics()
    b.validate("test_field", diag=d)

    diagnostics = d.diagnostics
    assert len(diagnostics) == 0
    assert b.blueprint_fragment(BlueprintContext.INPUT) == snapshot({'name': 'My boolean', 'selector': {'boolean': {}}})

    # Test convert method for None when allow_none is True
    assert b.convert(None) is None