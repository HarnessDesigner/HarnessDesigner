# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

import math
import build123d
from OpenGL import GL
from PySide6 import QtCore, QtWidgets

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...shapes import sleeve as _sleeve
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ... import color as _color
from ... import check_types as _check_types
from ...crash_dump import Attr, capturable


if TYPE_CHECKING:
    from ...ui.editor_3d import editor_3d as _editor_3d
    from .. import ObjectBase as _ObjectBase
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice
    from ... import ui as _ui
    from .. import wire as _wire_facade
    from ...gl import shaders as _shaders
    from ...database.global_db import splice as _global_splice


Config = _config.Config.editor_3d

# A solder sleeve (SHIELD_SLEEVE_DESIGN.md): the tube's colour when the part has none (or a clear / whitish one, which would almost vanish
# against the background: user, 2026-11-12), a translucent blue, and the solder ring on it.
# The tube is translucent (_SLEEVE_ALPHA of 255) so the ring, which lies inside its wall, shows through; the ring is solder, a silver grey.
_SLEEVE_COLOR = (70, 140, 225)
_SLEEVE_ALPHA = 120
_SLEEVE_LIGHT = 170     # a part colour whose darkest channel is above this (white, clear, natural) is drawn in _SLEEVE_COLOR instead
_RING_COLOR = (178, 181, 188)


@_check_types.do
def sleeve_tube_material(part: "_global_splice.Splice") -> "_materials.GLMaterial":
    """The translucent material of a solder sleeve's tube, for the 3D view and the peg board: the part's colour, or a translucent blue
    when it has none or a light one (see ``_SLEEVE_COLOR``).

    :param part: The catalog sleeve.
    :type part: :class:`_global_splice.Splice`
    """
    tube_color = part.color
    has_color = tube_color is not None and tube_color.db_id not in (None, b'\x00' * 16)
    tube_rgb = tuple(tube_color.ui.rgb)[:3] if has_color else _SLEEVE_COLOR

    if min(tube_rgb) > _SLEEVE_LIGHT:
        tube_rgb = _SLEEVE_COLOR

    return _materials.Plastic(_color.Color(*tube_rgb, _SLEEVE_ALPHA))


@_check_types.do
def _build_model(
        p1: _point.Point, p2: _point.Point, diameter: float
) -> tuple[build123d.Cylinder, tuple[_point.Point, _point.Point]]:
    """Build the model.

    UNKNOWN details are inferred from the callable name and signature.

    :param p1: Value for ``p1``.
    :type p1: :class:`_point.Point`
    :param p2: Value for ``p2``.
    :type p2: :class:`_point.Point`
    :param diameter: Value for ``diameter``.
    :type diameter: float
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    line = _line.Line(p1, p2)
    wire_length = line.length()
    wire_radius = diameter / 2.0 + 0.1

    # Create the wire
    model = build123d.Cylinder(float(wire_radius), float(wire_length), align=build123d.Align.NONE)

    bb = model.bounding_box()

    corner1 = _point.Point(*[item for item in bb.min])
    corner2 = _point.Point(*[item for item in bb.max])

    return model, (corner1, corner2)


@capturable()
class Splice(_base_3d.Base3D):
    """Represent a splice in :mod:`harness_designer.objects.objects_3d.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __dump_schema__ = (
        Attr('_part', severity=2),
        Attr('_p1', severity=2),
        Attr('_p2', severity=2),
        Attr('_p3', severity=2),
    )

    parent: "_splice.Splice" = None
    db_obj: "_pjt_splice.PJTSplice" = None

    @_check_types.do
    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):
        """Initialise the :class:`Splice` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_splice.Splice`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """

        with parent.mainframe.editor3d.context:
            self._part = db_obj.part

            self._p1 = db_obj.start_position3d
            self._p2 = db_obj.stop_position3d
            self._p3 = db_obj.branch_position3d

            angle = _angle.Angle.from_points(self._p1, self._p2)

            model = self._part.model3d

            length = self._part.length

            wires = db_obj.wires

            area1 = [0.0]
            area2 = [0.0]

            for wire in wires[0]:
                # `wire` is the project's row: the outside diameter belongs to its catalog part
                dia = float(wire.part.od_mm or 0.0)
                area = math.pi * ((dia / 2.0) ** 2.0)
                area1.append(area)

            for wire in wires[-1]:
                # `wire` is the project's row: the outside diameter belongs to its catalog part
                dia = float(wire.part.od_mm or 0.0)
                area = math.pi * ((dia / 2.0) ** 2.0)
                area2.append(area)

            area1_total = sum(area1)
            area2_total = sum(area2)

            if area1_total:
                dia1 = 2.0 * math.sqrt(area1_total / math.pi)
            else:
                dia1 = 0.0

            if area2_total:
                dia2 = 2.0 * math.sqrt(area2_total / math.pi)
            else:
                dia2 = 0.0

            if dia2 > dia1:
                dia = dia2
            else:
                dia = dia1

            scale = _point.Point(dia, dia, length)

            vbo = _cylinder.create_vbo()

            position = self._p1

            material = _materials.Rubber(self._part.color.ui)

            # A solder sleeve is not a plain cylinder: a hollow tube with a wall (shapes/sleeve.py), scaled by the diameter of the
            # cable it is on, with the solder ring (the cylinder primitive) on it, drawn by render().
            self._ring_vbo = None
            self._ring_material = None
            self._ring_shape = None
            self._ring_key = None
            self._ring_position = _point.Point(0.0, 0.0, 0.0)

            if self._part.is_solder_sleeve:
                on_cable = db_obj.shield_cable
                cable_od = on_cable[0].part.od_mm if on_cable is not None else 0.0

                self._ring_shape = shape = _sleeve.sizes(cable_od, self._part.min_dia, self._part.max_dia, self._part.length)
                scale = _point.Point(shape['diameter'], shape['diameter'], shape['length'])
                vbo = _sleeve.create_vbo()

                material = sleeve_tube_material(self._part)

                self._ring_vbo = _cylinder.create_vbo()
                self._ring_material = _materials.Metallic(_color.Color(*_RING_COLOR))

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    @_check_types.do
    def render(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw the splice. A solder sleeve is a translucent tube with its solder ring INSIDE the wall, so the ring is drawn first (an
        opaque cylinder, writing depth) and the tube over it, blended, without writing depth: the ring shows through the tube, and
        what the tube is drawn over (the cable, the ring) stays. A selected sleeve is drawn by the canvas's own translucent passes,
        which set the depth mask themselves, so it is left alone then.

        :param shaders: The canvas's shader programs.
        """
        if self._ring_vbo is None or not self.is_visible or self._vbo is not _sleeve.create_vbo():
            super().render(shaders)
            return

        self._render_ring(shaders)

        if self.is_selected:
            super().render(shaders)
            return

        GL.glDepthMask(GL.GL_FALSE)

        try:
            super().render(shaders)
        finally:
            GL.glDepthMask(GL.GL_TRUE)

    @_check_types.do
    def _render_ring(self, shaders: "_shaders.ShaderProgram") -> None:
        """Draw the solder ring of a sleeve: a cylinder inside the wall of the tube, centred on it along its axis, from the sleeve's
        start point to its stop point."""
        start = self._p1.as_numpy
        stop = self._p2.as_numpy
        key = (tuple(start), tuple(stop))

        if key != self._ring_key:
            axis = stop - start
            norm = float(math.sqrt(float((axis * axis).sum())))

            if norm < 1e-9:
                return

            at = start + axis / norm * self._ring_shape['ring_offset']
            self._ring_position = _point.Point(float(at[0]), float(at[1]), float(at[2]))
            self._ring_key = key

        shape = self._ring_shape
        ring_scale = _point.Point(shape['ring_diameter'], shape['ring_diameter'], shape['ring_length'])
        angle = self._ring_vbo.render_angle(self._angle)

        with shaders.faces:
            self._ring_material.set(shaders.faces)
            self._ring_vbo.render(shaders.faces, self._ring_position, angle, ring_scale, self.smooth)

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", wire: _Union["_wire_facade.Wire", None] = None
    ) -> _Union["_splice.Splice", None]:
        """Wire-snapping splice placement, ported from
        handlers.splice_handler.AddSpliceHandler. Always interactive --
        unlike Terminal's cavity-given Mode 1, there is no "everything
        already known" synchronous case here, since a splice always has
        to be snapped to a wire's exact position/orientation, either by
        the user's own mouse or (for the context-menu path) resolved
        against *wire*'s current geometry at commit time.

        A placeholder preview is armed immediately either way -- when
        *wire* is given and AWG-compatible it's replaced right away with
        a real one locked to that wire (matching AddSpliceHandler's own
        "immediately lock to it" __init__ behavior for the context-menu
        case); otherwise it stays an invisible placeholder until the
        first hover over a compatible wire recreates it (see
        add_handlers.editor_3d.splice.Splice._recreate_preview).
        """
        from ...handlers import splice_handler as _splice_handler
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db
        from ...add_handlers.editor_3d import splice as _add_splice
        from .. import splice as _splice_facade

        canvas = mainframe.editor3d.editor

        part_id = mainframe.editor_db.editor.splices.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.SplicesPage, mainframe.global_db.splices_table,
                'Add Splice')

            if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                part_id = dlg.GetValue()
            else:
                part_id = None

            dlg.deleteLater()

            if part_id is None:
                return None

        ptables = mainframe.project.ptables
        part = ptables.global_db.splices_table[part_id]

        preview_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.preview_color))
        compat_material = _materials.Plastic(
            _color.Color(*_config.Config.colors.add_object.wire_highlight))

        for w in mainframe.project.wires:
            if _splice_handler._wire_fits(part, w):  # NOQA
                w.identify(compat_material)

        # Degenerate but non-zero-length placeholder segment -- Splice's
        # own angle is only ever computed once, in __init__ (from p1/p2),
        # so a real (if meaningless) start/stop pair is needed even before
        # any wire has been picked; it's hidden until a real one replaces
        # it via hover.
        half = float(part.length) / 2.0
        start_db = ptables.pjt_points3d_table.insert(0.0, 0.0, -half)
        stop_db = ptables.pjt_points3d_table.insert(0.0, 0.0, half)
        branch_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)

        name = f'{part.manufacturer.name} {part.part_number}'

        db_obj = ptables.pjt_splices_table.insert(
            part_id, name, start_db.db_id, stop_db.db_id, branch_db.db_id, None, None)

        facade = _splice_facade.Splice(mainframe, db_obj)
        facade.identify(preview_material)
        facade.obj3d.is_visible = False

        handler = _add_splice.Splice(
            canvas, facade, part_id, part, preview_material, compat_material)

        facade.obj3d._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.obj3d

        if wire is not None and _splice_handler._wire_fits(part, wire):  # NOQA
            handler._recreate_preview(wire)  # NOQA
            facade = handler.target

        return facade

    @_check_types.do
    def handle_interaction(
        self, last_pos: _point.Point, current_pos: _point.Point, had_motion: bool,
        interaction_type: _interaction.MouseInteraction, clicked_object: _Union["_ObjectBase", None]
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to Base3D's own generic drag/rotation handling otherwise.
        """
        from ...add_handlers.editor_3d import splice as _add_splice  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_splice.Splice):
            # A local reference, not another read of self._active_handler
            # below -- a CANCEL can delete this object's own facade,
            # whose generic delete() sees self._active_handler is this
            # same handler and clears it right there, before this call
            # even returns (see objects_3d.wire.Wire.handle_interaction).
            handler = self._active_handler
            handled = handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if handler.is_finished and self._active_handler is handler:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)

    @property
    @_check_types.do
    def smooth(self) -> bool:
        smooth = self.db_obj.smooth
        if smooth is None:
            smooth = Config.renderer.smooth_splices

        return smooth

    @smooth.setter
    @_check_types.do
    def smooth(self, value: bool | None) -> None:
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def get_context_menu(self) -> "SpliceMenu":
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return SpliceMenu(self.mainframe.editor3d.editor, self)

    @property
    @_check_types.do
    def start_position(self) -> _point.Point:
        """Wire start position (Point instance)"""
        return self._p1

    @property
    @_check_types.do
    def wire_position(self) -> _point.Point:
        """Return the wire position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.branch_position

    @property
    @_check_types.do
    def branch_position(self) -> _point.Point:
        """Wire branch position (Point instance)"""
        return self._p3

    @property
    @_check_types.do
    def stop_position(self) -> _point.Point:
        """Wire stop position (Point instance)"""
        return self._p2


class SpliceMenu(QtWidgets.QMenu):
    """Represent a splice menu in :mod:`harness_designer.objects.objects_3d.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas: "_editor_3d.Editor3DPanel", selected: "Splice"):
        """Initialise the :class:`SpliceMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QtWidgets.QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Wire')
        action.triggered.connect(self.on_add_wire)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        action = self.addAction('Clone')
        action.triggered.connect(self.on_clone)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    @_check_types.do
    def on_add_wire(self) -> None:
        """Start the interactive wire placement flow, pinned to this
        splice's own branch point -- the part-search dialog (pre-filtered
        to wires whose diameter fits) opens immediately, straight into
        phase 1, same as a terminal's/cavity's own pinned Add Wire."""
        from . import wire as _wire_3d

        mainframe = self.selected.mainframe
        splice_obj = self.selected.parent

        @_check_types.do
        def _do() -> None:
            _wire_3d.Wire.start_add(mainframe, splice=splice_obj)

        QtCore.QTimer.singleShot(0, _do)

    @_check_types.do
    def on_trace_circuit(self) -> None:
        """Highlight every object on this splice's circuit."""
        _menu_ops.trace_circuit(self.selected)

    @_check_types.do
    def on_select(self) -> None:
        """Make this splice the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_clone(self) -> None:
        """Arm clone mode using this splice as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self) -> None:
        """Delete this splice from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self) -> None:
        """Show this splice's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
