from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from enum import IntEnum, auto
from typing import NamedTuple


class DiagnosticSeverity(IntEnum):
    ERROR = auto()
    WARNING = auto()
    DEBUG = auto()


class DiagnosticMessage(NamedTuple):
    severity: DiagnosticSeverity
    message: str
    context: str = ""


class Diagnostics:
    def __init__(
        self,
        diag_in: list[DiagnosticMessage] | None = None,
        diagnostic_level: DiagnosticSeverity = DiagnosticSeverity.WARNING,
        context: str = "",
    ):
        self._diagnostics: list[DiagnosticMessage] = [] if diag_in is None else diag_in
        self.diagnostic_level = diagnostic_level
        self.context = context
        self._has_error = False

    def _post(
        self,
        msg: str,
        severity: DiagnosticSeverity,
    ):
        """Post a diagnostic message to the diagnostics list with a field name."""
        if severity == DiagnosticSeverity.ERROR:
            self._has_error = True

        # Prepend the field name or path to the message if applicable.
        if severity <= self.diagnostic_level:
            self._diagnostics.append(
                DiagnosticMessage(severity=severity, message=msg, context=self.context)
            )

    def error(self, msg: str):
        """Post an error message to the diagnostics list."""
        self._post(msg, DiagnosticSeverity.ERROR)

    def warning(self, msg: str):
        """Post a warning message to the diagnostics list."""
        self._post(msg, DiagnosticSeverity.WARNING)

    def debug(self, msg: str):
        """Post a debug message to the diagnostics list."""
        self._post(msg, DiagnosticSeverity.DEBUG)

    def set_severity_level(self, severity: DiagnosticSeverity):
        self.diagnostic_level = severity

    @contextmanager
    def child(self, leaf: str | int | None = None) -> Generator[Diagnostics]:
        """Create a child context for the diagnostics object."""
        old_context = self.context

        if leaf is not None:
            self.context = (
                self.context + f".{leaf}"
                if isinstance(leaf, str)
                else self.context + f"[{leaf}]"
            )

        self.debug(f"Entering child context: {self.context}")
        try:
            yield self
        finally:
            self.context = old_context

    @property
    def diagnostics(self) -> list[DiagnosticMessage]:
        return self._diagnostics

    @property
    def has_error(self) -> bool:
        return self._has_error
