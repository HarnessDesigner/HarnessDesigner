# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import generic as _generic


class Generic(_base_pegboard.BasePegboard):
    """Peg-board representation of a generic object -- no rendering
    presence on the board."""
    _parent: "_generic.Generic" = None

    @_check_types.do
    def __init__(self, parent: "_generic.Generic"):
        """Initialise the :class:`Generic` instance.

        :param parent: Parent object.
        :type parent: :class:`_generic.Generic`
        """
        super().__init__(parent, None, position=None, angle=None)
