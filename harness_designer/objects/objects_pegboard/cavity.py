# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


class Cavity(_base_pegboard.BasePegboard):
    """Peg-board representation of a cavity.

    A cavity is a sub-feature of a housing, not an independently placed
    physical part -- it has no rendering presence of its own on the board
    (a seated terminal resolves through its housing's own anchor).
    """
    db_obj: "_pjt_cavity.PJTCavity"

    @_check_types.do
    def __init__(self, parent: "_cavity.Cavity", db_obj: "_pjt_cavity.PJTCavity"):
        """Initialise the :class:`Cavity` instance.

        :param parent: Parent object.
        :type parent: :class:`_cavity.Cavity`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cavity.PJTCavity`
        """

        # No vbo (never rendered directly -- a seated terminal/seal
        # reads its own independent position_pegboard/angle_pegboard,
        # same as objects_3d.terminal.Terminal/objects_3d.seal.Seal read
        # position3d/angle3d directly rather than deriving it from the
        # cavity at render time; whatever writes those columns at
        # seating/placement time is what actually needs the cavity's own
        # position/angle available to compute from). pjt_points_pegboard
        # already stores a real x/y/z (see PJTPointPegboard.point), so
        # angle_pegboard/position_pegboard are real, bound, Y-aware
        # values -- passing them through here (rather than None/None)
        # is what makes them available for that placement code to read.
        super().__init__(parent, db_obj, None, db_obj.angle_pegboard,
                         db_obj.position_pegboard, None, None)

    def render(self, _, __, ___):
        pass
