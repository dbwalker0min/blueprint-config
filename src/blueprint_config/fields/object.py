from __future__ import annotations

from typing import Any

from ..config import BlueprintConfig
from ..diagnostic import Diagnostics
from ..items import FieldItem
from ..types import MISSING, ParamTypeChk


class Object(FieldItem):
    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [
            ParamTypeChk("multiple", bool, False),
            ParamTypeChk("label_field", str, ""),
            ParamTypeChk("description_field", str, ""),
        ]
    )

    def convert(self, value: Any, diag: Diagnostics):
        # This would occur if there were an error during parsing
        if self._parent_class is None or (
            self._parent_class is not None
            and not issubclass(self._parent_class, BlueprintConfig)
        ):
            raise TypeError(
                f"'object_class' must be a class derived from 'BlueprintConfig'. "
                f"Is of type {type(self._parent_class).__name__!r}"
            )

        multiple = getattr(self, "multiple", False)
        allow_none = getattr(self, "allow_none", False)
        if value is None and allow_none:
            return [] if multiple else None

        if multiple:
            return [self._parent_class.from_dict(item) for item in value]

        return self._parent_class.from_dict(value)

    def selector(self) -> dict:
        # check the type on parent class. If it is None or it not a subclass of BlueprintConfig, return an empty dict
        if self._parent_class is None or not issubclass(
            self._parent_class, BlueprintConfig
        ):
            return {}

        obj: dict[str, Any] = {"fields": self._parent_class.blueprint_fragment()}

        if getattr(self, "multiple", False):
            obj["multiple"] = True

        if v := getattr(self, "label_field", MISSING) is not MISSING:
            obj["label_field"] = v

        if v := getattr(self, "description_field", MISSING) is not MISSING:
            obj["description_field"] = v

        return {"object": obj}
