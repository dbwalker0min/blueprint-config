# Naive values are intentional: selectors must not infer a timezone.
# ruff: noqa: DTZ001

import datetime as dt
import inspect
from typing import get_type_hints

import pytest
import yaml

from blueprint_config import (
    MISSING,
    BlueprintConfig,
    Date,
    DateTime,
    Diagnostics,
    EmbeddedObject,
    InputSection,
    Object,
    dump_yaml,
)

pytestmark = pytest.mark.review_required


@pytest.fixture(
    params=[
        (Date, "date", "2024-02-29", dt.date(2024, 2, 29)),
        (DateTime, "datetime", "2024-02-29 13:30:00", dt.datetime(2024, 2, 29, 13, 30)),
    ]
)
def case(request):
    return request.param


def bind(field):
    class Config(BlueprintConfig):
        blueprint_name = "Calendar settings"
        value = field

    return Config


@pytest.mark.reviewed(False)
def test_conversion_and_public_imports(case):
    selector, key, text, expected = case
    from blueprint_config import fields
    from blueprint_config.fields.date import Date as ModuleDate
    from blueprint_config.fields.datetime import DateTime as ModuleDateTime

    assert ModuleDate is Date is fields.Date
    assert ModuleDateTime is DateTime is fields.DateTime
    config_type = bind(selector())
    assert config_type.get_build_diagnostics() == []
    for value in (text, expected):
        config = config_type.from_dict({"value": value})
        assert config.value == expected
        assert type(config.value) is type(expected)
        assert config.get_load_diagnostics() == []
    assert config_type.blueprint_fragment() == {"value": {"selector": {key: {}}}}
    assert get_type_hints(selector.__init__)["section"] == InputSection | None
    assert all(
        p.kind is inspect.Parameter.KEYWORD_ONLY
        for n, p in inspect.signature(selector).parameters.items()
        if n not in ("args", "kwargs")
    )


@pytest.mark.parametrize("as_string", [True, False])
@pytest.mark.parametrize("allow_none", [True, False])
@pytest.mark.reviewed(False)
def test_defaults_and_yaml(case, as_string, allow_none):
    selector, key, text, expected = case
    config_type = bind(
        selector(
            default=text if as_string else expected,
            allow_none=allow_none,
            name="When",
            description="First line\n    Second line",
        )
    )
    assert config_type.get_build_diagnostics() == []
    assert config_type().value == expected
    assert config_type(value=None).value == expected
    override = "2025-01-01" if selector is Date else "2025-01-01 00:00:00"
    assert config_type(value=override).value != expected
    fragment = config_type.blueprint_fragment()
    assert fragment["value"] == {
        "name": "When",
        "description": "First line\nSecond line",
        "default": text,
        "selector": {key: {}},
    }
    assert yaml.safe_load(dump_yaml(fragment)) == fragment
    # BaseLoader also tolerates the generated !input tags.
    blueprint = yaml.load(config_type.build_blueprint(), Loader=yaml.BaseLoader)
    assert blueprint["blueprint"]["input"]["value"]["default"] == text


@pytest.mark.reviewed(False)
def test_optional_missing_and_required(case):
    selector, _, _, _ = case
    optional = bind(selector(default=MISSING, allow_none=True))
    assert optional().value is None
    assert optional(value=None).value is None
    assert "default" not in optional.blueprint_fragment()["value"]
    required = bind(selector())
    assert required().get_load_diagnostics()[0].context == ".value"
    diag = Diagnostics()
    assert required.value.convert(None, diag) is MISSING
    assert diag.has_error
    assert len(diag.diagnostics) == 1
    assert "no default" in diag.diagnostics[0].message


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": 1},
        {"description": False},
        {"allow_none": 1},
        {"section": "options"},
        {"default": None},
        {"default": False},
        {"default": 0},
        {"default": []},
        {"default": {}},
        {"default": dt.time(12)},
        {"default": ""},
        {"default": "2023-02-29"},
        {"default": "garbage"},
    ],
)
@pytest.mark.reviewed(False)
def test_invalid_declarations(case, kwargs):
    config_type = bind(case[0](**kwargs))
    diagnostics = config_type.get_build_diagnostics()
    assert len(diagnostics) == 1
    assert diagnostics[0].severity.name == "ERROR"


@pytest.mark.parametrize("value", [False, 0, 1.5, [], {}, dt.time(12)])
@pytest.mark.reviewed(False)
def test_invalid_runtime_types_even_with_default(case, value):
    selector, _, text, _ = case
    field = bind(selector(default=text)).value
    diag = Diagnostics()
    assert field.convert(value, diag) is MISSING
    assert diag.has_error
    assert len(diag.diagnostics) == 1


@pytest.mark.parametrize(
    "selector,value",
    [
        (Date, "2023-02-29"),
        (Date, "2024-13-01"),
        (Date, "2024-01-32"),
        (Date, "20240229"),
        (Date, "2024-W09-4"),
        (Date, "2024-02-29 12:00:00"),
        (Date, dt.datetime(2024, 2, 29)),
        (DateTime, dt.date(2024, 2, 29)),
        (DateTime, "2024-02-29"),
        (DateTime, "2023-02-29 12:00:00"),
        (DateTime, "2024-02-29 24:00:00"),
        (DateTime, "2024-02-29 12:60:00"),
        (DateTime, "2024-02-29 12:00:60"),
        (DateTime, "2024-02-29X12:00:00"),
        (DateTime, "2024-02-29 123000"),
        (DateTime, "20240229T12:30:00"),
        (DateTime, "2024-02-29 12:30:00 trailing"),
        (Date, ""),
        (DateTime, ""),
        (Date, "no date"),
        (DateTime, "no date"),
    ],
)
@pytest.mark.reviewed(False)
def test_invalid_values_and_defaults(selector, value):
    config_type = bind(selector())
    diag = Diagnostics()
    with diag.child(leaf="value"):
        assert config_type.value.convert(value, diag) is MISSING
    assert len(diag.diagnostics) == 1
    assert diag.has_error
    assert diag.diagnostics[0].context == ".value"
    loaded = config_type(value=value)
    assert loaded.value is MISSING
    assert loaded.get_load_diagnostics() == diag.diagnostics
    invalid = bind(selector(default=value))
    assert len(invalid.get_build_diagnostics()) == 1
    assert "default" not in invalid.blueprint_fragment()["value"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("2024-02-29T13:30", dt.datetime(2024, 2, 29, 13, 30)),
        ("2024-02-29 13:30:45.123456", dt.datetime(2024, 2, 29, 13, 30, 45, 123456)),
        ("2024-02-29T13:30:00Z", dt.datetime(2024, 2, 29, 13, 30, tzinfo=dt.UTC)),
        (
            "2024-02-29 13:30:00-07:00",
            dt.datetime(
                2024, 2, 29, 13, 30, tzinfo=dt.timezone(dt.timedelta(hours=-7))
            ),
        ),
    ],
)
@pytest.mark.reviewed(False)
def test_datetime_precision_and_offsets(text, expected):
    config_type = bind(DateTime(default=text))
    assert config_type().value == expected
    assert config_type(value=text).value == expected
    assert config_type(value=expected).value is expected
    default = yaml.safe_load(dump_yaml(config_type.blueprint_fragment()))["value"][
        "default"
    ]
    assert isinstance(default, str)
    assert dt.datetime.fromisoformat(default) == expected


@pytest.mark.reviewed(False)
def test_constructor_records_unknown_options_and_positional_arguments(case):
    selector = case[0]
    for kwargs in ({"min": "2024-01-01"}, {"read_only": True}, {"defualt": "oops"}):
        config_type = bind(selector("When", default=case[2], **kwargs))
        diagnostics = config_type.get_build_diagnostics()
        assert len(diagnostics) == 2
        assert all(
            d.severity.name == "ERROR" and d.context == ".value" for d in diagnostics
        )
        assert "positional argument" in diagnostics[0].message
        assert next(iter(kwargs)) in diagnostics[1].message
        assert config_type().value == case[3]


@pytest.mark.reviewed(False)
def test_sections_and_embedded_objects(case):
    selector, key, text, expected = case

    class Config(BlueprintConfig):
        blueprint_name = "Calendar settings"
        options = InputSection(name="Options", collapsed=True)
        value = selector(default=text, section=options)

    assert Config.get_build_diagnostics() == []
    assert Config().value == expected
    assert Config.blueprint_fragment()["options"]["input"]["value"] == {
        "default": text,
        "selector": {key: {}},
    }

    class Settings(EmbeddedObject):
        value = selector(name="When", default=text)
        optional = selector(allow_none=True)

    class Parent(BlueprintConfig):
        blueprint_name = "Nested calendar settings"
        settings = Object(object_type=Settings)

    assert Settings.get_build_diagnostics() == []
    assert Settings.blueprint_fragment()["value"] == {
        "label": "When",
        "selector": {key: {}},
    }
    config = Parent(settings={"value": text})
    assert config.settings.value == expected
    assert config.settings.optional is None
    assert Settings().value == expected


@pytest.mark.reviewed(False)
def test_datetime_default_preserves_fractional_offset():
    offset = dt.timezone(dt.timedelta(hours=1, seconds=30, microseconds=123456))
    expected = dt.datetime(2024, 2, 29, 13, 30, tzinfo=offset)
    config_type = bind(DateTime(default=expected))
    assert config_type.get_build_diagnostics() == []
    assert config_type().value == expected
    assert config_type().value.utcoffset() == expected.utcoffset()
    default = yaml.safe_load(dump_yaml(config_type.blueprint_fragment()))["value"][
        "default"
    ]
    assert config_type(value=default).value == expected
