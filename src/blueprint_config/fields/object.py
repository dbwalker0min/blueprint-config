from __future__ import annotations

from typing import Any

from ..config import EmbeddedObject
from ..diagnostic import Diagnostics
from ..items import FieldItem
from ..types import MISSING, ParamTypeChk


class Object(FieldItem):
    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [
            ParamTypeChk("object_type", type, MISSING),
            ParamTypeChk("default", (dict, list), MISSING),
            ParamTypeChk("multiple", bool, False),
            ParamTypeChk("label_field", str, ""),
            ParamTypeChk("description_field", str, ""),
        ]
    )

    def _consume_arg(self, param_chk: ParamTypeChk):
        if param_chk.param != "object_type":
            return super()._consume_arg(param_chk)

        # Config classes use ABCMeta, so the shared exact-type check is unsuitable.
        object_type = self._field_args.pop("object_type", MISSING)
        self.object_type: type[EmbeddedObject] | None = None
        if isinstance(object_type, type) and issubclass(object_type, EmbeddedObject):
            self.object_type = object_type
        else:
            assert self._validate_diagnostics is not None
            self._validate_diagnostics.error(
                f"From field {self._field_name!r}: "
                "'object_type' must be a class derived from 'EmbeddedObject'"
            )
        self._valid_fields.add("object_type")

    def _get_object_type(self) -> type[EmbeddedObject]:
        object_type = getattr(self, "object_type", None)
        if object_type is None:
            raise TypeError(
                "'object_type' must be a class derived from 'EmbeddedObject'"
            )
        return object_type

    def convert(self, value: Any, diag: Diagnostics):
        object_type = self._get_object_type()

        multiple = getattr(self, "multiple", False)
        value = self._resolve_none(value, diag)
        if value is None:
            return [] if multiple else None

        if multiple:
            return [object_type.from_dict(item) for item in value]

        return object_type.from_dict(value)

    def selector(self) -> dict:
        obj: dict[str, Any] = {"fields": self._get_object_type().blueprint_fragment()}

        if getattr(self, "multiple", False):
            obj["multiple"] = True

        if v := getattr(self, "label_field", ""):
            obj["label_field"] = v

        if v := getattr(self, "description_field", ""):
            obj["description_field"] = v

        return {"object": obj}
