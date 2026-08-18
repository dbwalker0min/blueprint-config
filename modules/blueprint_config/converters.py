import datetime as dt

from stubs.pyscript_builtins import pyscript_compile


@pyscript_compile
def convert_time(value: str | dt.time | None) -> dt.time | None:
    """Convert an ISO string to a datetime"""
    return dt.time.fromisoformat(value) if isinstance(value, str) else value

