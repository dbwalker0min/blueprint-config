from __future__ import annotations

import datetime as dt

from ..diagnostic import Diagnostics
from ..items import FieldItem


class Time(FieldItem):
    def convert(self, value: str | dt.time, diag: Diagnostics | None = None):
        if isinstance(value, str):
            return dt.time.fromisoformat(value)

        return value

    def selector(self) -> dict:
        return {"time": {}}
