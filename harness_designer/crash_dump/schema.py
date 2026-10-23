"""Per-class capture-list primitives: the vocabulary used to declare, on a
class body, exactly which attributes and properties a crash dump may read.
"""
from __future__ import annotations

from .. import check_types as _check_types


class Attr:
    __slots__ = ('name', 'severity')

    @_check_types.do
    def __init__(self, name: str, severity: int):
        self.name = name
        self.severity = severity

    @_check_types.do
    def __repr__(self) -> str:
        return f'Attr({self.name!r}, severity={self.severity})'


def dump_property(severity: int):
    """Mark a ``@property`` as capturable at the given severity.

    Must be stacked below ``@property`` (closer to ``def``) -- the tag is
    stashed on the plain getter function, since a ``property`` object
    itself has no ``__dict__`` to hold arbitrary attributes::

        @property
        @dump_property(severity=2)
        def wire_position_pegboard_id(self):
            ...
    """
    def decorator(func):
        func._dump_severity = severity
        return func
    return decorator
