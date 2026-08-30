from inline_snapshot import snapshot

from blueprint_config.diagnostic import (
    DiagnosticMessage,
    Diagnostics,
    DiagnosticSeverity,
)
from blueprint_config.types import Status


def test_button_diagnostics_simple():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.WARNING)

    diagnostics.error("This is an error message", "field1")
    diagnostics.warning("This is a warning message", "field2")
    diagnostics.debug("This is a debug message", "field3")

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 2
    assert diag_list[0] == DiagnosticMessage(
        severity=DiagnosticSeverity.ERROR,
        message="From field 'field1': This is an error message",
    )
    assert diag_list[1] == DiagnosticMessage(
        severity=DiagnosticSeverity.WARNING,
        message="From field 'field2': This is a warning message",
    )


def test_at_level_debug():
    diagnostics = Diagnostics()

    diagnostics.set_severity_level(DiagnosticSeverity.DEBUG)

    diagnostics.error("This is an error message", "field1")
    diagnostics.warning("This is a warning message", "field2")
    diagnostics.debug("This is a debug message", "field3")

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 3
    assert diag_list[0] == DiagnosticMessage(
        severity=DiagnosticSeverity.ERROR,
        message="From field 'field1': This is an error message",
    )
    assert diag_list[1] == DiagnosticMessage(
        severity=DiagnosticSeverity.WARNING,
        message="From field 'field2': This is a warning message",
    )
    assert diag_list[2] == DiagnosticMessage(
        severity=DiagnosticSeverity.DEBUG,
        message="From field 'field3': This is a debug message",
    )


def test_type_check_error():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.DEBUG)

    result = diagnostics.type_check_error(
        field_name="field1",
        parameter_name="param1",
        expected_type=int,
        value="string",
    )
    assert result == Status.INVALID

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 1
    assert diag_list[0] == DiagnosticMessage(
        severity=DiagnosticSeverity.ERROR,
        message="From field 'field1': Type check failed for parameter 'param1' of field 'field1': expected type int, got type str",
    )
    assert diagnostics.has_error is True

def test_type_check_okay():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.DEBUG)

    result = diagnostics.type_check_error(
        field_name="field1",
        parameter_name="param1",
        expected_type=int,
        value=123,
    )

    diag_list = diagnostics.diagnostics
    assert result == Status.VALID
    assert len(diag_list) == 0
    assert diagnostics.has_error is False


def test_diagnostic_no_field_name():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.DEBUG)

    diagnostics.error("This is an error message")

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 1
    assert diag_list[0] == DiagnosticMessage(
        severity=DiagnosticSeverity.ERROR, message="This is an error message"
    )
    assert diagnostics.has_error is True


def test_diagnostics_with_path():
    d0 = Diagnostics(diagnostic_level=DiagnosticSeverity.DEBUG)

    d0.error("This is an error message", use_path=True)

    d1 = d0.child("leaf1")
    d2: Diagnostics = d1.child(1)

    d2.error("This is another error message", use_path=True)

    d0.error("This is a third error message", use_path=True)

    diag_list = d0.diagnostics

    assert len(diag_list) == 3
    assert diag_list == snapshot(
        [
            DiagnosticMessage(
                severity=DiagnosticSeverity.ERROR,
                message="From path 'root': This is an error message",
            ),
            DiagnosticMessage(
                severity=DiagnosticSeverity.ERROR,
                message="From path 'leaf1[1]': This is another error message",
            ),
            DiagnosticMessage(
                severity=DiagnosticSeverity.ERROR,
                message="From path 'root': This is a third error message",
            ),
        ]
    )
    assert d0.has_error is True
