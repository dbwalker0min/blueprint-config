from blueprint_config.diagnostic import (
    DiagnosticMessage,
    Diagnostics,
    DiagnosticSeverity,
)


def test_simple():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.WARNING)

    diagnostics.error("This is an error message", "field1")
    diagnostics.warning("This is a warning message", "field2")
    diagnostics.debug("This is a debug message", "field3")

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 2
    assert diag_list[0] == DiagnosticMessage(
        severity=DiagnosticSeverity.ERROR, message="From field 'field1': This is an error message"
    )
    assert diag_list[1] == DiagnosticMessage(
        severity=DiagnosticSeverity.WARNING, message="From field 'field2': This is a warning message"
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
        severity=DiagnosticSeverity.ERROR, message="From field 'field1': This is an error message"
    )
    assert diag_list[1] == DiagnosticMessage(
        severity=DiagnosticSeverity.WARNING, message="From field 'field2': This is a warning message"
    )
    assert diag_list[2] == DiagnosticMessage(
        severity=DiagnosticSeverity.DEBUG, message="From field 'field3': This is a debug message"
    )

def test_type_check_error():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.DEBUG)

    diagnostics.type_check_error(
        field_name="field1",
        parameter_name="param1",
        expected_type=int,
        value="string",
    )

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 1
    assert diag_list[0] == DiagnosticMessage(
        severity=DiagnosticSeverity.ERROR,
        message="From field 'field1': Type check failed for parameter 'param1' of field 'field1': expected type int, got type str"
    )

def test_type_check_okay():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.DEBUG)

    diagnostics.type_check_error(
        field_name="field1",
        parameter_name="param1",
        expected_type=int,
        value=123,
    )

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 0

def test_diagnostic_no_field_name():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.DEBUG)

    diagnostics.error("This is an error message")

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 1
    assert diag_list[0] == DiagnosticMessage(
        severity=DiagnosticSeverity.ERROR, message="This is an error message"
    )