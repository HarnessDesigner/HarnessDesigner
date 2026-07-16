# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import basepeg as _basepeg


if TYPE_CHECKING:
    from .. import wire_marker as _wire_marker
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker


class WireMarker(_basepeg.BasePeg):
    """Peg-board representation of a wire marker.

    A wire marker is an annotation/sub-feature of a wire, not an
    independently placed physical part -- it has no rendering presence on
    the board.
    """
    db_obj: "_pjt_wire_marker.PJTWireMarker"

    def __init__(self, parent: "_wire_marker.WireMarker",
                 db_obj: "_pjt_wire_marker.PJTWireMarker"):
        """Initialise the :class:`WireMarker` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire_marker.WireMarker`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_marker.PJTWireMarker`
        """
        _basepeg.BasePeg.__init__(self, parent, db_obj, position=None, angle=None)
