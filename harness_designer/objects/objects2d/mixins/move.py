# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>


from ....geometry import point as _point
from ....geometry import line as _line
from ....wrappers.decimal import Decimal as _decimal


class MoveMixin:
    """Represent a move mixin in :mod:`harness_designer.objects.objects2d.mixins.move`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _parent = None
    _db_obj = None

    _position: _point.Point = None

    @property
    def position(self) -> _point.Point:
        """Return the position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self._position


