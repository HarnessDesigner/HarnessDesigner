# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Click-to-place session for a cable in the 3D editor.

The wire's session (:mod:`~harness_designer.add_handlers.editor_3d.wire`) with everything that attaches taken out: a
cable's ends are free (a terminal or splice is attached to a conductor, after the cable is split), so there is no
snapping, no compatibility check and no circuit. The first click sets the start, each further click commits a waypoint,
and a right click ends the cable at the last waypoint, which is when its conductors are made from its final end points
(``PJTCableConductorsTable.insert_for_cable``), it is seeded onto the peg board (the 3D route unfolded flat) and it joins
the project. Cancelling deletes the cable.
"""

from typing import TYPE_CHECKING

from . import wire as _wire_add
from ...geometry import point as _point
from ...database.global_db.mixins import wire_conductor as _wire_conductor
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_cable_path as _pjt_cable_path


class Cable(_wire_add.Wire):
    """The placement session of a cable."""

    @property
    @_check_types.do
    def _paths_table(self) -> "_pjt_cable_path.PJTCablePathsTable":
        """The cable routes table: a cable's route is not kept with the wires'."""
        return self.ptables.pjt_cable_paths_table

    @property
    @_check_types.do
    def _waypoints_get_layouts(self) -> bool:
        """A cable with no outer jacket (twisted or ribbon) has no layout at its waypoints: its conductors are what get
        laid out, once the cable is split. A jacketed cable keeps them.

        :rtype: bool
        """
        return self.target.db_obj.part.cable_style not in (_wire_conductor.CableStyle.TWISTED,
                                                           _wire_conductor.CableStyle.RIBBON)

    @_check_types.do
    def _ensure_snap_probes(self) -> None:
        """A cable snaps to nothing, so there are no probes to build."""

    @_check_types.do
    def _hover_phase0(self, mouse_pos: _point.Point) -> None:
        """Have the start point follow the cursor.

        :param mouse_pos: The cursor.
        :type mouse_pos: :class:`_point.Point`
        """
        self._update_preview_stop(self.camera.get_position_on_focal_plane(mouse_pos))

    @_check_types.do
    def _hover_phase1(self, mouse_pos: _point.Point) -> None:
        """Have the end being placed follow the cursor.

        :param mouse_pos: The cursor.
        :type mouse_pos: :class:`_point.Point`
        """
        self._update_preview_stop(self.camera.get_position_on_focal_plane(mouse_pos))

    @_check_types.do
    def _handle_first_click(self, mouse_pos: _point.Point) -> None:
        """Lock the start where the hover left it and begin growing the other end.

        :param mouse_pos: The cursor.
        :type mouse_pos: :class:`_point.Point`
        """
        self._start_circuit_id = None

        self._clear_hover()
        self._overlay.hide_message()

        self._growing_point = self.target.obj3d.stop_position
        self._phase = 1

    @_check_types.do
    def _handle_second_click(self, mouse_pos: _point.Point) -> None:
        """Commit a waypoint where the end being placed is.

        :param mouse_pos: The cursor.
        :type mouse_pos: :class:`_point.Point`
        """
        self._commit_waypoint()

    @_check_types.do
    def finalize_at_last_point(self) -> None:
        """End the cable at the last committed waypoint, make its conductors and add it to the project. Does nothing
        before the start is set; cancels the cable when no waypoint was committed."""
        if self._finalized or self._phase == 0:
            return

        if not self._has_committed_waypoint:
            self._finalized = True
            self.cancel()
            return

        self._promote_last_committed()

        cable = self.target

        self.ptables.pjt_cable_conductors_table.insert_for_cable(cable.db_obj)

        # the conductors' end points follow the cable's only once the cable object has made them live
        for conductor in cable.db_obj.conductors:
            conductor.start_position3d  # NOQA
            conductor.stop_position3d  # NOQA

        # the cable's presence on the peg board: its final 3D route, unfolded flat (as a bundle's is)
        cable.objpegboard.seed_from_3d()

        self.mainframe.project.add_cable(cable)
        cable.conductors_made()

        self._cleanup()
        self._destroy_overlay()
        self._finalized = True
