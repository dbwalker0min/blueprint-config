from __future__ import annotations

from enum import IntEnum, auto
from typing import Any, NamedTuple

from .types import MISSING, Status


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
        path: tuple[str | int, ...] = (),
    ):
        self._diagnostics: list[DiagnosticMessage] = diag_in or []
        self.diagnostic_level = diagnostic_level
        self.path = path

    def _format_path(self) -> str:
        """Format the current path as a string."""
        elements: list[str] = []
        for e in self.path:
            if isinstance(e, str):
                elements.append(f'.{e}')
            elif isinstance(e, int):
                elements.append(f'[{e}]')
        path = ''.join(elements).lstrip('.').replace('.]', ']')
        if path == '':
            path = "root"
        return "'" + path + "'"
    
    def _post(
        self,
        msg: str,
        severity: DiagnosticSeverity,
        *,
        field_name: str | None,
        use_path: bool = False,
    ):
        """Post a diagnostic message to the diagnostics list with a field name."""
        # Prepend the field name or path to the message if applicable.
        if field_name:
            msg = f"From field {field_name!r}: {msg}"
        elif use_path:
            msg = f"From path {self._format_path()}: {msg}"
        if severity <= self.diagnostic_level:
            self._diagnostics.append(DiagnosticMessage(severity=severity, message=msg))

    def error(self, msg: str, field_name: str | None = None, use_path: bool = False):
        """Post an error message to the diagnostics list."""
        self._post(msg, DiagnosticSeverity.ERROR, field_name=field_name, use_path=use_path)

    def warning(self, msg: str, field_name: str | None = None, use_path: bool = False):
        """Post a warning message to the diagnostics list."""
        self._post(msg, DiagnosticSeverity.WARNING, field_name=field_name, use_path=use_path)

    def debug(self, msg: str, field_name: str | None = None, use_path: bool = False):
        """Post a debug message to the diagnostics list."""
        self._post(msg, DiagnosticSeverity.DEBUG, field_name=field_name, use_path=use_path)

    def set_severity_level(self, severity: DiagnosticSeverity):
        self.diagnostic_level = severity

    def child(self, leaf: str | int | None = None) -> Diagnostics:
        """Create a child diagnostics object with an extended path."""
        return Diagnostics(
            diag_in=self._diagnostics,
            diagnostic_level=self.diagnostic_level,
            path=self.path if leaf is None else (self.path + (leaf,))
        )

    @property
    def diagnostics(self) -> list[DiagnosticMessage]:
        return self._diagnostics

    def type_check_error(
        self,
        field_name: str,
        parameter_name: str,
        expected_type: type,
        value: Any,
        allow_missing: bool = False,
    ) -> Status:
        """Post a type check error to the diagnostics list if the type of the value
        does not match the expected type. This is only called on classes. There's
        no concept of paths.
        """
        error_detected = False
        if allow_missing and value is MISSING:
            return Status.VALID

        value_type = type(value)
        if expected_type is not value_type:
            error_detected = True
            msg = (
                f"Type check failed for parameter {parameter_name!r} "
                f"of field {field_name!r}: expected type {expected_type.__name__}, "
                f"got type {value_type.__name__}"
            )
            self.error(msg, field_name)
        return Status.INVALID if error_detected else Status.VALID
