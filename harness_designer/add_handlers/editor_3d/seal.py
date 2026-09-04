# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Seal placement for the 3D editor -- what
``objects.objects_3d.seal.Seal.start_add`` was given (*housing*/
*terminal*/*cavity*) decides which project-wide scope to search, but for
*housing* specifically it's the picked part's own **category** (SWS/
MAT/PLUG/ACC -- see ``database.global_db.seal_type.SealType.category``)
that decides what happens next, not a separate flag chosen before the
part is even known. See TODO.md's own "Seal placement design spec"
entry for the full spec this was built against.

*housing* given, category PLUG
    Preview snaps interactively to this housing's own empty cavities.
*housing* given, category SWS
    Preview snaps interactively to this housing's own terminals that
    are seated in a cavity (never a bare cavity) -- a terminal whose
    seated wire doesn't fit this seal's own opening is still snappable,
    just flagged with a distinct highlight color (see
    ``handlers.seal_handler.wire_seal_fit_ok``).
*housing* given, any other category (MAT/ACC)
    Instant -- seated on the housing's own pre-defined seal slot,
    no interactive session.
*terminal* only
    SWS seal at the midpoint of the terminal's own cavity. Instant.
*cavity* only
    Plug or dummy pin placed on the cavity. Instant.
Nothing given
    Free interactive placement; snaps to housings, terminals, or empty
    cavities project-wide depending on the chosen seal's own category.

Every mode still arms an interactive session and waits for a
confirming click (see ``_finalize``'s own ``is_instant`` branch) --
only the two housing-interactive cases and the free mode actually move
the preview around during hover (see ``hover``'s own early-return on
``self._is_instant``).
"""

from typing import TYPE_CHECKING

import numpy as np

from ...gl.canvas_base import interaction as _interaction
from ...handlers import handler_base as _handler_base
from ...geometry import point as _point
from ...objects import housing as _housing
from ...objects import terminal as _terminal
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects


@_check_types.do
def cavity_midpoint(pjt_cavity):
    """World-space midpoint of *pjt_cavity* along its insertion axis."""
    cpos_np = pjt_cavity.position3d.as_numpy.astype(np.float64)
    cav_ang = pjt_cavity.angle3d
    length = float(pjt_cavity.part.length)
    ref_local = np.array([[0.0, 0.0, length]], dtype=np.float64)
    ref_world = np.asarray(ref_local @ cav_ang, dtype=np.float64)[0] + cpos_np
    mid = (cpos_np + ref_world) / 2.0

    return float(mid[0]), float(mid[1]), float(mid[2])


@_check_types.do
def cavity_plug_pns(mainframe, max_dim: float) -> list:
    """PLUG and dummy-pin seal part numbers whose dimensions fit *max_dim*."""
    if max_dim <= 0.0:
        return []

    mainframe.global_db.seals_table.execute(
        'SELECT DISTINCT s.part_number FROM seals s '
        'JOIN seal_types st ON s.type_id = st.id '
        'WHERE (UPPER(st.name) = "PLUG" OR UPPER(st.name) = "DUMMY PIN") '
        'AND (s.width <= ? OR s.o_dia <= ?);',
        (max_dim, max_dim))

    return [row[0] for row in mainframe.global_db.seals_table.fetchall()]


class Seal(_base.AddHandlerBase):
    """Category-driven seal placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase",
        housing: "_housing.Housing | None", terminal: "_terminal.Terminal | None",
        cavity, is_instant: bool, snap_targets: list, is_dummy_pin: bool
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._housing = housing
        self._terminal = terminal
        self._cavity = cavity
        self._is_instant = is_instant
        self._snap_targets = snap_targets
        self._is_dummy_pin = is_dummy_pin
        self._snapped = None
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @_check_types.do
    def __call__(
        self, last_pos, current_pos, had_motion: bool,
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        if self._finalized:
            return False

        if interaction_type is _interaction.MouseInteraction.CANCEL:
            self.cancel()
            self._finalized = True
            return True

        if interaction_type is _interaction.MouseInteraction.MOVE:
            self.hover(current_pos)
            return True

        if interaction_type is _interaction.MouseInteraction.LEFT_UP and not had_motion:
            self._finalize()
            return True

        return False

    @property
    @_check_types.do
    def snap_pool(self):
        from ... import utils as _utils

        objects = []
        positions = []

        for target in self._snap_targets:
            if not target.is_in_3dview:
                continue

            if isinstance(target, _housing.Housing):
                positions.append(target.db_obj.seal_position3d)
            elif isinstance(target, _terminal.Terminal):
                positions.append(target.db_obj.wire_position3d)
            else:  # Cavity
                pjt_cav = target.db_obj
                if self._is_dummy_pin:
                    gender = pjt_cav.housing.part.gender.name.lower()
                    if gender == 'male':
                        x, y, z = pjt_cav.position3d.as_float
                    else:
                        x, y, z = cavity_midpoint(pjt_cav)
                else:
                    x, y, z = cavity_midpoint(pjt_cav)

                positions.append(_point.Point(x, y, z))

            objects.append(target)

        return _utils.SnapPool(objects, positions)

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        if self._is_instant:
            return

        # Snap by perpendicular distance from the actual mouse ray, not
        # by distance from a point unprojected onto the camera's own
        # arbitrary focal-plane depth -- see SnapPool.query_ray's own
        # docstring (same fix as add_handlers.editor_3d.terminal.
        # Terminal.hover). Only the free-floating fallback (nothing
        # snapped) still wants a single point.
        snap_pool = self.snap_pool
        origin, direction = self.camera.get_mouse_ray(mouse_pos)
        snapped = snap_pool.query_ray(origin, direction) if origin is not None else None

        prev_snapped = self._snapped

        if snapped is None:
            point = self.camera.get_position_on_focal_plane(mouse_pos)
            self._snapped = None
            if prev_snapped is not None:
                _handler_base.HandlerBase.reset_angle(self.target)

        else:
            if isinstance(snapped, _housing.Housing):
                point = snapped.db_obj.seal_position3d
                if prev_snapped is not snapped:
                    _handler_base.HandlerBase.set_angle_from_housing(self.target, snapped)

            elif isinstance(snapped, _terminal.Terminal):
                point = snapped.db_obj.wire_position3d
                pjt_cav = snapped.db_obj.cavity
                if prev_snapped is not snapped:
                    if pjt_cav is not None:
                        _handler_base.HandlerBase.set_angle_from_cavity(self.target, pjt_cav)
                    else:
                        _handler_base.HandlerBase.reset_angle(self.target)

            else:  # Cavity
                pjt_cav = snapped.db_obj
                if self._is_dummy_pin:
                    gender = pjt_cav.housing.part.gender.name.lower()
                    if gender == 'male':
                        x, y, z = pjt_cav.position3d.as_float
                    else:
                        x, y, z = cavity_midpoint(pjt_cav)
                else:
                    x, y, z = cavity_midpoint(pjt_cav)

                point = _point.Point(x, y, z)

                if prev_snapped is not snapped:
                    _handler_base.HandlerBase.set_angle_from_cavity(self.target, pjt_cav)

            self._snapped = snapped

        position = self.target.db_obj.position3d
        delta = point - position
        position += delta

    @_check_types.do
    def _finalize(self) -> None:
        if not self._is_instant:
            if self._snapped is None:
                return

            if isinstance(self._snapped, _housing.Housing):
                for h in self.mainframe.project.housings:
                    h.identify(None)

                self._snapped.db_obj.seal_position3d.attach(self.target.db_obj.position3d)
                self.target.db_obj.housing_id = self._snapped.db_obj.db_id
                _handler_base.HandlerBase.set_angle_from_housing(self.target, self._snapped)

            elif isinstance(self._snapped, _terminal.Terminal):
                for t in self.mainframe.project.terminals:
                    t.identify(None)

                pjt_cav = self._snapped.db_obj.cavity
                if pjt_cav is not None:
                    _handler_base.HandlerBase.set_angle_from_cavity(self.target, pjt_cav)

                self.target.db_obj.terminal_id = self._snapped.db_obj.db_id

            else:  # Cavity
                for cav in self.mainframe.project.cavities:
                    cav.identify(None)

                _handler_base.HandlerBase.set_angle_from_cavity(self.target, self._snapped.db_obj)
                self.target.db_obj.cavity_id = self._snapped.db_obj.db_id

        self._finalized = True
        self.mainframe.project.add_seal(self.target)

    @_check_types.do
    def _clear_highlights(self) -> None:
        for target in self._snap_targets:
            target.identify(None)

    @_check_types.do
    def cancel(self) -> None:
        self._clear_highlights()

        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
