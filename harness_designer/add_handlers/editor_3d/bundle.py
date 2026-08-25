# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Wire-snapping bundle-cover placement for the 3D editor.

Ported from ``handlers.bundle_handler.AddBundleHandler`` -- always
free/interactive (the original handler takes no housing/wire argument
at all; mainframe.py's own toolbar branch used to pass a second
``selected`` positional that ``AddBundleHandler.__init__`` never
accepted, an outright ``TypeError`` on every use -- dropped here rather
than ported). Same delete-and-recreate-on-wire-change preview shape as
:class:`add_handlers.editor_3d.splice.Splice`, since a bundle's own
start/stop points are fixed to span the wire's full length the moment
a wire is picked.
"""

from typing import TYPE_CHECKING

from ...gl.canvas_base import interaction as _interaction
from ...gl import object_picker as _object_picker
from ...geometry import point as _point
from ...objects import wire as _wire
from .. import base as _base
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...gl.canvas_3d import canvas as _canvas
    from ... import objects as _objects


@_check_types.do
def _wire_fits_bundle(bundle_part, wire) -> bool:
    """Return True when the wire's OD falls within the bundle cover's
    diameter range."""
    part = wire.db_obj.part
    if part is None:
        return False

    wire_od = part.od_mm
    if wire_od is None:
        return False

    min_dia = bundle_part.min_dia
    max_dia = bundle_part.max_dia
    if min_dia is not None and wire_od < min_dia:
        return False

    if max_dia is not None and wire_od > max_dia:
        return False

    return True


class Bundle(_base.AddHandlerBase):
    """Wire-snapping bundle-cover placement -- see the module docstring."""

    @_check_types.do
    def __init__(
        self, canvas: "_canvas.Canvas", target: "_objects.ObjectBase", part_id: bytes,
        part, preview_material
    ):
        super().__init__(canvas, target)

        self.mainframe = canvas.mainframe
        self.camera = canvas.camera

        self._part_id = part_id
        self._part = part
        self._preview_material = preview_material
        self._preview_conc_db = None
        self._snapped_wire = None
        self._finalized = False

    @property
    @_check_types.do
    def is_finished(self) -> bool:
        return self._finalized

    @staticmethod
    def _get_view_object(obj):
        return obj.obj3d

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

    @_check_types.do
    def _bundle_diameter(self, wire: "_wire.Wire") -> float:
        if wire.db_obj.part:
            wire_od = float(wire.db_obj.part.od_mm or 0.0)
        else:
            wire_od = 0.0

        return max(float(self._part.min_dia), wire_od)

    @_check_types.do
    def hover(self, mouse_pos: _point.Point) -> None:
        picked = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera, self._get_view_object)

        wire = picked if isinstance(picked, _wire.Wire) else None

        if wire is None or not _wire_fits_bundle(self._part, wire):
            if self.target is not None:
                self.target.obj3d.is_visible = False

            self._snapped_wire = None
            return

        if wire is not self._snapped_wire:
            self._recreate_preview(wire)

        if self.target is not None:
            self.target.obj3d.is_visible = True

    @_check_types.do
    def _recreate_preview(self, wire: "_wire.Wire") -> None:
        from ...objects import bundle as _bundle_facade

        if self.target is not None:
            self.target.delete()
            self.target = None

        p1_np = wire.obj3d.start_position.as_numpy
        p2_np = wire.obj3d.stop_position.as_numpy

        ptables = self.mainframe.project.ptables
        start_db = ptables.pjt_points3d_table.insert(*p1_np.tolist())
        stop_db = ptables.pjt_points3d_table.insert(*p2_np.tolist())

        name = f'{self._part.manufacturer.name} {self._part.part_number}'
        bundle_db = ptables.pjt_bundles_table.insert(self._part_id, name)
        bundle_db.start_position3d_id = start_db.db_id
        bundle_db.stop_position3d_id = stop_db.db_id

        # Empty concentric so Bundle 3D __init__ can call concentric.layers
        # safely.
        self._preview_conc_db = ptables.pjt_concentrics_table.insert(
            bundle_db.db_id, None)

        facade = _bundle_facade.Bundle(self.mainframe, bundle_db)
        facade.identify(self._preview_material)

        diameter = self._bundle_diameter(wire)
        facade.obj3d._diameter = diameter  # NOQA
        facade.obj3d.scale.x = diameter
        facade.obj3d.scale.y = diameter

        self.target = facade
        facade.obj3d._active_handler = self  # NOQA
        self.canvas.active_handler_obj = facade.obj3d

        self._snapped_wire = wire

    @_check_types.do
    def _finalize(self) -> None:
        if self._snapped_wire is None or self.target is None:
            return

        for w in self.mainframe.project.wires:
            w.identify(None)

        self._finalized = True

        wire = self._snapped_wire

        wire.obj3d.start_position.attach(self.target.obj3d.start_position)
        wire.obj3d.stop_position.attach(self.target.obj3d.stop_position)

        diameter = self._bundle_diameter(wire)
        ptables = self.mainframe.project.ptables
        layer_db = ptables.pjt_concentric_layers_table.insert(
            0, 1, 0, self._preview_conc_db.db_id, diameter)

        ptables.pjt_concentric_wires_table.insert(
            layer_db.db_id, 0, wire.db_obj.db_id, False)

        self.target.identify(None)
        self.mainframe.project.add_bundle(self.target)

    @_check_types.do
    def cancel(self) -> None:
        for w in self.mainframe.project.wires:
            w.identify(None)

        if self.target is not None:
            self.target.delete()
            self.target = None

    @_check_types.do
    def delete(self) -> None:
        if not self._finalized:
            self.cancel()
            self._finalized = True
