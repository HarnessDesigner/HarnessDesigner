# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_pegboard as _base_pegboard
from . import chain_edges as _chain_edges
from ... import check_types as _check_types
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_layout as _pjt_wire_layout
    from .. import wire_layout as _wire_layout


Config = _config.Config.editor_pegboard


class WireLayout(_base_pegboard.BasePegboard):
    """
    Peg-board representation of a wire layout (grab handle) -- a bare
    position along its wire's path, no independent geometry/rendering
    presence or rotation of its own.
    """
    _parent: "_wire_layout.WireLayout" = None
    db_obj: "_pjt_wire_layout.PJTWireLayout"

    @_check_types.do
    def __init__(self, parent: "_wire_layout.WireLayout",
                 db_obj: "_pjt_wire_layout.PJTWireLayout"):
        """Initialise the :class:`WireLayout` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire_layout.WireLayout`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_layout.PJTWireLayout`
        """

        # No vbo/angle -- a layout point is a bare position along its
        # wire's path, no independent rendering presence or rotation of
        # its own (see base_pegboard.BasePegboard.__init__'s vbo-is-None
        # branch). position=None whenever position_pegboard_id is NULL
        # (this layout isn't placed on the peg-board view yet) -- handled
        # gracefully by BaseVar (can_drag()/drag() both no-op on a None
        # position).
        super().__init__(parent, db_obj, position=db_obj.position_pegboard)

        self.point3d_id = db_obj.position_pegboard_id

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_wires

        return smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def touching_budgets(self) -> list:
        """Return the length budget(s) for the wire segment(s) touching
        this waypoint -- always two (previous/next), since a wire-layout
        point is always strictly interior to its wire's chain.

        Resolves this waypoint's own row (``pjt_points_pegboard``) to
        find which wire it belongs to, then delegates the actual chain
        walk to that wire's own
        ``objects.objects_pegboard.wire.Wire.touching_edges``.
        """
        if self.point3d_id is None:
            return []

        project = self.parent.mainframe.project
        waypoint_row = project.ptables.pjt_points_pegboard_table[self.point3d_id]

        if waypoint_row.wire_id is None:
            return []

        wire_db_obj = project.ptables.pjt_wires_table[waypoint_row.wire_id]
        return _chain_edges.touching_edges(wire_db_obj, self.point3d_id)
