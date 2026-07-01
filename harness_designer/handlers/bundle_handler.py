# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Interactive handler logic for placing bundle covers over wires.

Single-click workflow: hovering over a compatible wire shows a preview bundle
auto-sized from the wire's start point to its stop point.  A click finalises
placement, creating the bundle DB record and a concentric layer containing the
covered wire.
"""

from PySide6.QtWidgets import QDialog
from typing import TYPE_CHECKING

from . import handler_base as _handler_base
from ..geometry import point as _point
from ..gl.canvas3d import object_picker as _object_picker
from ..objects import bundle as _bundle
from ..objects import wire as _wire
from ..gl import materials as _materials
from .. import config as _config
from ..ui.dialogs import part_search as _part_search
from ..ui import editor_db as _editor_db
from .. import color as _color


if TYPE_CHECKING:
    from .. import ui as _ui


Config = _config.Config.colors


def _wire_fits_bundle(bundle_part, wire) -> bool:
    """
    Return True when the wire's OD falls within the bundle cover's diameter range.
    """
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


class AddBundleHandler(_handler_base.HandlerBase):
    """Handle interactive placement of a bundle cover over an existing wire.

    Hover snaps to the nearest compatible wire and shows a preview cylinder
    that auto-sizes to span from the wire's start to its stop point.  A single
    click finalises the placement.
    """
    obj: "_bundle.Bundle" = None
    _preview_conc_db = None

    def __init__(self, mainframe: "_ui.MainFrame"):
        part_id = mainframe.editor_db.editor.bundle_covers.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.BundleCoversPage,
                title='Add Bundle Cover',
                table=mainframe.global_db.bundle_covers_table)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()

            dlg.deleteLater()

        super().__init__(mainframe, part_id)

        self._preview_material = _materials.Plastic(
            _color.Color(*Config.add_object.preview_color))
        self._wire_highlight_material = _materials.Plastic(
            _color.Color(*Config.add_object.wire_highlight))

        self._snapped_wire: "_wire.Wire | None" = None
        self.part: "_db_bundle_cover.BundleCover | None" = None

        if part_id is None:
            self._finalized = True
            return

        self.part = mainframe.global_db.bundle_covers_table[part_id]
        self._highlight_compatible_wires()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _highlight_compatible_wires(self):
        for w in self.mainframe.project.wires:
            if _wire_fits_bundle(self.part, w):
                w.identify(self._wire_highlight_material)

    def _clear_wire_highlights(self):
        for w in self.mainframe.project.wires:
            w.identify(None)

    def _bundle_diameter(self, wire: "_wire.Wire") -> float:
        wire_od = float(wire.db_obj.part.od_mm or 0.0) if wire.db_obj.part else 0.0
        return max(float(self.part.min_dia), wire_od)

    def _create_preview(self, wire: "_wire.Wire"):
        """Rebuild the preview bundle sized to *wire*'s full span."""
        if self.obj is not None:
            self.obj.delete()
            self.obj = None

        p1_np = wire.obj3d.start_position.as_numpy
        p2_np = wire.obj3d.stop_position.as_numpy

        start_db = self.ptables.pjt_points3d_table.insert(*p1_np.tolist())
        stop_db = self.ptables.pjt_points3d_table.insert(*p2_np.tolist())

        name = f'{self.part.manufacturer.name} {self.part.part_number}'
        bundle_db = self.ptables.pjt_bundles_table.insert(self.part_id, name)
        bundle_db.start_position3d_id = start_db.db_id
        bundle_db.stop_position3d_id = stop_db.db_id

        # Empty concentric so Bundle 3D __init__ can call concentric.layers safely.
        self._preview_conc_db = self.ptables.pjt_concentrics_table.insert(
            bundle_db.db_id, None)

        self.obj = _bundle.Bundle(self.mainframe, bundle_db)
        self.obj.identify(self._preview_material)
        self._snapped_wire = wire

        # Override diameter to reflect the actual wire OD.
        diameter = self._bundle_diameter(wire)
        self.obj.obj3d._diameter = diameter
        self.obj.obj3d.scale.x = diameter
        self.obj.obj3d.scale.y = diameter

    # ------------------------------------------------------------------
    # Handler protocol
    # ------------------------------------------------------------------

    def hover(self, mouse_pos: _point.Point):
        if self._finalized:
            return

        selected = _object_picker.find_object(
            mouse_pos, self.camera.objects_in_view, self.camera)
        wire = selected if isinstance(selected, _wire.Wire) else None

        if wire is None or not _wire_fits_bundle(self.part, wire):
            if self.obj is not None:
                self.obj.obj3d.is_visible = False
            self._snapped_wire = None
            return

        if wire is not self._snapped_wire:
            self._create_preview(wire)

        if self.obj is not None:
            self.obj.obj3d.is_visible = True

    def release_capture(self):
        if self._finalized:
            return

        if self._captured_position is None:
            return

        if self._snapped_wire is None or self.obj is None:
            return

        self._clear_wire_highlights()
        self._finalized = True

        wire = self._snapped_wire

        # Attach the wire's real endpoints to the preview's temp points.
        wire.obj3d.start_position.attach(self.obj.obj3d.start_position)
        wire.obj3d.stop_position.attach(self.obj.obj3d.stop_position)

        # Add a concentric layer containing the wire to the preview's concentric.
        diameter = self._bundle_diameter(wire)
        layer_db = self.ptables.pjt_concentric_layers_table.insert(
            0, 1, 0, self._preview_conc_db.db_id, diameter)
        self.ptables.pjt_concentric_wires_table.insert(
            layer_db.db_id, 0, wire.db_obj.db_id, False)

        self.obj.identify(None)
        self.mainframe.project.add_bundle(self.obj)
        self.obj = None

    def cancel(self):
        self._clear_wire_highlights()
        if self.obj is not None:
            self.obj.delete()
            self.obj = None
