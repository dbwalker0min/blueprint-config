from __future__ import annotations

from enum import IntEnum, auto
from typing import Any, NamedTuple


class DiagnosticSeverity(IntEnum):
    ERROR = auto()
    WARNING = auto()
    DEBUG = auto()


class DiagnosticMessage(NamedTuple):
    severity: DiagnosticSeverity
    message: str


class Diagnostics:
    def __init__(
        self,
        diag_in: list[DiagnosticMessage] | None = None,
        diagnostic_level: DiagnosticSeverity = DiagnosticSeverity.WARNING,
    ):
        self._diagnostics: list[DiagnosticMessage] = diag_in or []
        self.diagnostic_level = diagnostic_level

    def _post(self, msg: str, field_name: str | None, severity: DiagnosticSeverity):
        """Post a diagnostic message to the diagnostics list with a field name."""
        if field_name:
            msg = f"From field {field_name!r}: {msg}"
        if severity <= self.diagnostic_level:
            self._diagnostics.append(DiagnosticMessage(message=msg, severity=severity)) 

    def error(self, msg: str, field_name: str | None = None):
        """Post an error message to the diagnostics list."""
        self._post(msg, field_name, DiagnosticSeverity.ERROR)

    def warning(self, msg: str, field_name: str | None = None):
        """Post a warning message to the diagnostics list."""
        self._post(msg, field_name, DiagnosticSeverity.WARNING)

    def debug(self, msg: str, field_name: str | None = None):
        """Post a debug message to the diagnostics list."""
        self._post(msg, field_name, DiagnosticSeverity.DEBUG)

    def set_severity_level(self, severity: DiagnosticSeverity):
        self.diagnostic_level = severity


    @property
    def diagnostics(self) -> list[DiagnosticMessage]:
        return self._diagnostics

    def type_check_error(
        self, field_name: str, parameter_name: str, expected_type: type, value: Any
    ):
        value_type = type(value)
        if value is not None and expected_type is not value_type:
            msg = (
                f"Type check failed for parameter {parameter_name!r} "
                f"of field {field_name!r}: expected type {expected_type.__name__}, "
                f"got type {value_type.__name__}"
            )
            print(msg)
            self.error(msg, field_name)
            

