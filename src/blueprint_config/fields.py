from __future__ import annotations

import datetime as dt
from collections.abc import Collection
from typing import Any

from .diagnostic import Diagnostics
from .items import ConfigObject, FieldItem
from .types import MISSING, ParamTypeChk, Status, _Missing


class Boolean(FieldItem):
    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [
            ParamTypeChk("default", bool, False),
        ]
    )

    def convert(self, value: bool | None, diag: Diagnostics):
        if isinstance(value, bool):
            return value

        if value is None:
            if v:=getattr(self, "default", MISSING) is not MISSING:
                return v

            if v:=getattr(self, "allow_none", False):
                return None

            diag.error("No value provided for Boolean field with no default and 'allow_none' false")

        # This shouldn't happen, as all cases should be handled above.
        raise TypeError(f"Value of Boolean is not boolean or None {value!r}")

    def selector(self) -> dict:
        return {"boolean": {}}

    def validate(self, field_name: str, diag: Diagnostics):
        super().validate(field_name, diag, valid_properties)

        # just check the type of the default value.
        diag.type_check_error(field_name, "default", bool, self.default, True)


class Time(Field):
    def convert(self, value: str | dt.time, diag: Diagnostics | None = None):
        if isinstance(value, str):
            return dt.time.fromisoformat(value)

        return value

    def selector(self) -> dict:
        return {"time": {}}

    def validate(
        self, field_name: str, diag: Diagnostics, valid_properties: Collection[str]
    ):
        super().validate(field_name, diag, valid_properties)

        # check the default type
        d = self.default
        if d is not MISSING and d is not None:
            diag.type_check_error(field_name, "default", dt.time, d)


class Object(Field):
    def __init__(
        self,
        object_type: type[ConfigObject] | _Missing = MISSING,
        *,
        multiple: bool | _Missing = MISSING,
        label_field: str | _Missing = MISSING,
        description_field: str | _Missing = MISSING,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.object_class = object_type
        self.multiple = False if multiple is MISSING else multiple
        self.label_field = label_field
        self.description_field = description_field

    def validate(
        self, field_name: str, diag: Diagnostics, valid_properties: Collection[str]
    ):
        super().validate(field_name, diag, valid_properties)

        # Check multiple is a boolean
        diag.type_check_error(field_name, "multiple", bool, self.multiple)

        # Check `object_type` is a class derived from `ConfigObject`
        ot = self.object_class
        if ot is MISSING:
            diag.error(
                "'object_type' must be a class derived from 'ConfigObject'. Is missing",
                field_name,
            )
            return
        if isinstance(ot, type):
            if not issubclass(ot, ConfigObject):
                class_heir: list[str] = [
                    f"'{cls.__name__}'" for cls in ot.__mro__[1:] if cls is not object
                ]
                if len(class_heir) == 0:
                    class_heir = ["nothing"]
                heir_str = "->".join(class_heir)
                m = (
                    "'object_type' must be a class derived from 'ConfigObject'. "
                    f"Class {type(ot).__name__!r} is derived from {heir_str}"
                )
                diag.error(m, field_name)
                return

            # check that the label and description fields are valid field names
            field_names = ot.fields()
            for p in ["label_field", "description_field"]:
                value = getattr(self, p)
                if value is MISSING:
                    continue
                if (
                    diag.type_check_error(
                        field_name, p, str, value, allow_missing=False
                    )
                    == Status.VALID
                    and value not in field_names
                ):
                    m = (
                        f"parameter {p!r} ({value!r}) does not reference "
                        f"a valid field in {ot.__name__!r}."
                    )
                    diag.error(m, field_name)
            return

        diag.error(
            f"'object_type' must be a class derived from 'ConfigObject'. "
            f"Is of type {type(ot).__name__!r}",
            field_name,
        )
        # Finally, I need to make sure that the default (if specified) can be loaded
        if self.default is not MISSING:
            try:
                self.convert(self.default)
            except Exception as e:
                diag.error(
                    f"Failed to load default value for field '{field_name}': {e}",
                    field_name,
                )

    def convert(self, value: Any):
        # This would occur if there were an error during parsing
        if not (
            isinstance(self.object_class, type)
            and issubclass(self.object_class, EmbeddedObject)
        ):
            raise TypeError(
                f"'object_class' must be a class derived from 'EmbeddedObject'. "
                f"Is of type {type(self.object_class).__name__!r}"
            )

        if value is None and self.allow_none:
            return [] if self.multiple else None

        if self.multiple:
            return [self.object_class.from_dict(item) for item in value]

        return self.object_class.from_dict(value)

    def selector(self) -> dict:
        if not (
            isinstance(self.object_class, type)
            and issubclass(self.object_class, EmbeddedObject)
        ):
            return {}

        obj: dict[str, Any] = {"fields": self.object_class.blueprint_fragment()}

        if self.multiple:
            obj["multiple"] = True

        if self.label_field is not MISSING:
            obj["label_field"] = self.label_field

        if self.description_field is not MISSING:
            obj["description_field"] = self.description_field

        return {"object": obj}
