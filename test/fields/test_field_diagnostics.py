import datetime as dt

import pytest

from blueprint_config import (
    MISSING,
    BlueprintConfig,
    Boolean,
    Date,
    DateTime,
    Diagnostics,
    DiagnosticSeverity,
    EmbeddedObject,
    InputSection,
    Number,
    Object,
)
from blueprint_config.fields import Time

pytestmark = pytest.mark.review_required


@pytest.mark.reviewed(False)
@pytest.mark.parametrize("use_from_dict", [False, True])
def test_mixed_fields_collect_all_errors_and_load_later_values(use_from_dict):
    class Config(BlueprintConfig):
        blueprint_name = "Accumulate mixed errors"
        flag = Boolean()
        day = Date()
        timestamp = DateTime()
        time = Time()
        required = Boolean()
        level = Number()
        valid = Boolean(default=False)
        midnight = Time(default="00:00:00")

    values = {
        "flag": "no",
        "day": "bad",
        "timestamp": False,
        "time": "25:00:00",
        "level": [],
        "extra": 1,
    }
    config = Config.from_dict(values) if use_from_dict else Config(**values)
    diagnostics = config.get_load_diagnostics()
    assert [(d.context, d.severity.name) for d in diagnostics] == [
        (".flag", "ERROR"),
        (".day", "ERROR"),
        (".timestamp", "ERROR"),
        (".time", "ERROR"),
        (".required", "ERROR"),
        (".level", "ERROR"),
        ("", "WARNING"),
    ]
    for name in ("flag", "day", "timestamp", "time", "required", "level"):
        assert getattr(config, name) is MISSING
    assert config.valid is False
    assert config.midnight == dt.time(0)


@pytest.mark.reviewed(False)
def test_build_errors_accumulate_across_fields_and_sections():
    class Config(BlueprintConfig):
        blueprint_name = "All declarations inspected"
        options = InputSection("Options", typo=True)
        flag = Boolean("Flag", typo=True)
        day = Date("Day", typo=True)
        timestamp = DateTime("Timestamp", typo=True)
        time = Time("Time", typo=True)
        valid = Boolean(default=False)

    diagnostics = Config.get_build_diagnostics()
    assert len(diagnostics) == 10
    assert all(d.severity.name == "ERROR" for d in diagnostics)
    assert [d.context for d in diagnostics] == [
        ".options",
        ".options",
        ".flag",
        ".flag",
        ".day",
        ".day",
        ".timestamp",
        ".timestamp",
        ".time",
        ".time",
    ]
    assert Config.valid.default is False


@pytest.mark.reviewed(False)
def test_nested_lists_aggregate_errors_and_warnings_with_complete_paths():
    class Entry(EmbeddedObject):
        flag = Boolean()
        day = Date()
        valid = Boolean(default=False)

    class Group(EmbeddedObject):
        entries = Object(object_type=Entry, multiple=True)

    class Config(BlueprintConfig):
        blueprint_name = "Nested errors"
        groups = Object(object_type=Group, multiple=True)
        later = Boolean(default=False)

    config = Config(
        groups=[
            {
                "entries": [
                    {"flag": "invalid", "day": "bad", "extra": 1},
                    42,
                    {"flag": True, "day": "2024-02-29"},
                ]
            },
            {"entries": [{"day": "2024-02-29"}]},
        ]
    )
    assert [(d.context, d.severity.name) for d in config.get_load_diagnostics()] == [
        (".groups[0].entries[0].flag", "ERROR"),
        (".groups[0].entries[0].day", "ERROR"),
        (".groups[0].entries[0]", "WARNING"),
        (".groups[0].entries[1]", "ERROR"),
        (".groups[1].entries[0].flag", "ERROR"),
    ]
    assert config.groups[0].entries[0].flag is MISSING
    assert config.groups[0].entries[1] is MISSING
    assert config.groups[0].entries[2].flag is True
    assert config.groups[0].entries[2].day == dt.date(2024, 2, 29)
    assert config.later is False
    assert config.groups[0].entries[0].get_load_diagnostics()[0].context == ".flag"
    assert Config(groups=[]).get_load_diagnostics() == []


@pytest.mark.reviewed(False)
def test_nested_diagnostics_update_error_status_and_preserve_local_paths():
    class Entry(EmbeddedObject):
        flag = Boolean()

    class Config(BlueprintConfig):
        blueprint_name = "Nested diagnostics"
        value = Object(object_type=Entry)

    diag = Diagnostics(diagnostic_level=DiagnosticSeverity.ERROR)
    with diag.child("value"):
        nested = Config.value.convert({"flag": "invalid", "extra": True}, diag)
    assert diag.has_error
    assert diag.context == ""
    assert len(diag.diagnostics) == 1
    assert diag.diagnostics[0].context == ".value.flag"
    assert len(nested.get_load_diagnostics()) == 2
    assert nested.get_load_diagnostics()[0].context == ".flag"


@pytest.mark.reviewed(False)
@pytest.mark.parametrize("selector", [Boolean, Date, DateTime, Time])
def test_explicit_none_accumulates_one_error_per_required_scalar(selector):
    class Config(BlueprintConfig):
        blueprint_name = "Required values"
        first = selector()
        second = selector()
        later = Boolean(default=False)

    config = Config(first=None, second=None)
    assert config.first is config.second is MISSING
    assert [d.context for d in config.get_load_diagnostics()] == [".first", ".second"]
    assert config.later is False
