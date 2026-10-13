from typing import Any

from ..diagnostic import Diagnostics
from ..items import BlueprintItem
from ..types import MISSING, ParamTypeChk


class InputSection(BlueprintItem):
    """A top-level group of blueprint inputs; sections cannot be nested."""

    FIELD_PARAM_TYPE_CHECKS: frozenset[ParamTypeChk] = frozenset(
        [
            ParamTypeChk("icon", str, ""),
            ParamTypeChk("collapsed", bool, False),
        ]
    )

    def validate_inputs(self, diag: Diagnostics) -> None:
        """Check nesting and defaults after all declarations have been validated."""
        if self.section is not None:
            diag.error(
                f"Input section {self._field_name!r} cannot be nested in another section"
            )
        if not self.collapsed:
            return
        assert self._parent_class is not None, "Parent class must not be None"
        for name, field in self._parent_class.field_items().items():
            if field.section is self and getattr(field, "default", MISSING) is MISSING:
                diag.error(
                    f"Input {name!r} in collapsed section {self._field_name!r} "
                    "must have a default value"
                )

    def selector(self) -> dict[str, Any]:
        assert self._parent_class is not None, "Parent class must not be None"

        result = {}

        # This is a special case
        # Do not render the variables at this level.
        # They are rendered in the level above
        # if self.name:
        #     result["name"] = self.name

        # if self.description:
        #     result["description"] = self.description

        # # if not emitted, this field defaults to false
        # if self.collapsed:
        #     result["collapsed"] = True

        inputs = {}

        # Find all the fields that reference this object
        for f, v in self._parent_class.field_items().items():
            if v.section is self:
                inputs[f] = self._parent_class.render_field(v)

        return result | inputs
