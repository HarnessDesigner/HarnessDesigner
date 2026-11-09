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

import numpy as np

from . import wire as _wire_add
from ...geometry import point as _point
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_cable_path as _pjt_cable_path


# A click this close (mm) to the point the previous click set adds no waypoint: two coincident waypoints are a bend that
# cannot be seen and cannot be grabbed apart
_SAME_SPOT_MM = 1.0


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
        """No cable has a layout at its waypoints (WAYPOINT_REWORK_DESIGN.md): its route is drawn with rounded corners like a
        wire's, and the only layouts a cable shows are the markers where the conductors of a split-out cable join the broken
        out wires (``Cable._make_split_markers``).

        :rtype: bool
        """
        return False

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
    def _commit_waypoint(self) -> None:
        """Commit a waypoint where the end being placed is, unless it is where the previous point already is.

        A click on the spot the last one set (the same click delivered twice, or a second click without moving) would add a waypoint
        on top of the one before it: a second bend that cannot be seen, and that comes apart from the first the moment either is
        dragged. The first click after the start is compared with the start.
        """
        cable = self.target.obj3d
        is_start = self._growing_point is cable.start_position

        if is_start:
            other_end = cable.stop_position
        else:
            other_end = cable.start_position

        waypoints = [row.point.as_numpy for row in self.target.db_obj.waypoints3d]

        if not waypoints:
            previous = other_end.as_numpy
        elif is_start:
            previous = waypoints[0]
        else:
            previous = waypoints[-1]

        gap = np.asarray(self._growing_point.as_numpy, dtype=np.float64) - np.asarray(previous, dtype=np.float64)

        if float(np.linalg.norm(gap)) < _SAME_SPOT_MM:
            return

        super()._commit_waypoint()

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
