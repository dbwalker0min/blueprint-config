
class _Missing:
    """This is a sentinel value to indicate that a field has no default value"""
    __slots__ = ()

    def __repr__(self):
        return "MISSING"

MISSING = _Missing()