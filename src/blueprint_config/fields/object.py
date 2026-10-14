from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ..diagnostic import Diagnostics
from ..items import FieldItem
from ..types import MISSING, ParamTypeChk

if TYPE_CHECKING:
    from ..config import EmbeddedObject


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

        from ..config import EmbeddedObject

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

    def validate(self, parent, field_name: str, diag: Diagnostics | None):
        super().validate(parent, field_name, diag)
        assert diag is not None
        if self.object_type is not None and self.default is not MISSING:
            default_diag = Diagnostics()
            with default_diag.child(field_name), default_diag.child("default"):
                self.convert(self.default, default_diag)
            diag.extend(default_diag.diagnostics)
            if default_diag.has_error:
                self.default = MISSING

    def _convert_one(self, value: Any, diag: Diagnostics):
        if not isinstance(value, Mapping) or any(not isinstance(k, str) for k in value):
            diag.error("Object value must be a mapping with string keys")
            return MISSING
        instance = self.object_type.from_dict(value)
        diag.extend(instance.get_load_diagnostics())
        return instance

    def convert(self, value: Any, diag: Diagnostics):
        if self.object_type is None:
            diag.error("'object_type' must be a class derived from 'EmbeddedObject'")
            return MISSING

        multiple = getattr(self, "multiple", False)
        value = self._resolve_none(value, diag)
        if value is MISSING:
            return MISSING
        if value is None:
            return [] if multiple else None

        if multiple:
            if not isinstance(value, list):
                diag.error("Multiple Object value must be a list of mappings")
                return MISSING
            result = []
            for index, item in enumerate(value):
                with diag.child(index):
                    result.append(self._convert_one(item, diag))
            return result

        return self._convert_one(value, diag)

    def selector(self) -> dict:
        # Invalid declarations already have build errors; rendering stays inspectable.
        obj: dict[str, Any] = {
            "fields": self.object_type.blueprint_fragment() if self.object_type else {}
        }

        if getattr(self, "multiple", False):
            obj["multiple"] = True

        if v := getattr(self, "label_field", ""):
            obj["label_field"] = v

        if v := getattr(self, "description_field", ""):
            obj["description_field"] = v

        return {"object": obj}
