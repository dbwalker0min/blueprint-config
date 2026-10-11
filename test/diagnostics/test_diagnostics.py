from inline_snapshot import snapshot

from blueprint_config import DiagnosticMessage, DiagnosticSeverity
from blueprint_config.diagnostic import Diagnostics


def test_button_diagnostics_simple():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.WARNING)

    diagnostics.error("This is an error message")
    diagnostics.warning("This is a warning message")
    diagnostics.debug("This is a debug message")

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 2
    assert diag_list == snapshot()


def test_at_level_debug():
    diagnostics = Diagnostics()

    diagnostics.set_severity_level(DiagnosticSeverity.DEBUG)

    diagnostics.error("This is an error message")
    diagnostics.warning("This is a warning message")
    diagnostics.debug("This is a debug message")

    diag_list = diagnostics.diagnostics
    assert diag_list == snapshot(
        [
            DiagnosticMessage(
                severity=DiagnosticSeverity.ERROR, message="This is an error message"
            ),
            DiagnosticMessage(
                severity=DiagnosticSeverity.WARNING, message="This is a warning message"
            ),
            DiagnosticMessage(
                severity=DiagnosticSeverity.DEBUG, message="This is a debug message"
            ),
        ]
    )


def test_diagnostic_no_field_name():
    diagnostics = Diagnostics(diagnostic_level=DiagnosticSeverity.DEBUG)

    diagnostics.error("This is an error message")

    diag_list = diagnostics.diagnostics

    assert len(diag_list) == 1
    assert diag_list[0] == DiagnosticMessage(
        severity=DiagnosticSeverity.ERROR, message="This is an error message"
    )
    assert diagnostics.has_error is True
