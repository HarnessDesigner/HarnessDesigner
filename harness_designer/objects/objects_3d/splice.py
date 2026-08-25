# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
from PySide6.QtWidgets import QMenu
import build123d

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from . import base_3d as _base_3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ... import color as _color
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice
    from ... import ui as _ui
    from .. import wire as _wire_facade


Config = _config.Config.editor_3d


@_check_types.do
def _build_model(p1: _point.Point, p2: _point.Point, diameter: float):
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


class Splice(_base_3d.Base3D):
    """Represent a splice in :mod:`harness_designer.objects.objects_3d.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
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
                dia = wire.od_mm
                area = math.pi * ((dia / 2.0) ** 2.0)
                area1.append(area)

            for wire in wires[-1]:
                dia = wire.od_mm
                area = math.pi * ((dia / 2.0) ** 2.0)
                area2.append(area)

            area1 = sum(area1)
            area2 = sum(area2)

            if area1:
                dia1 = 2.0 * math.sqrt(area1 / math.pi)
            else:
                dia1 = 0.0

            if area2:
                dia2 = 2.0 * math.sqrt(area2 / math.pi)
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

            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", wire: "_wire_facade.Wire | None" = None
    ) -> "_splice.Splice | None":
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
        from PySide6.QtWidgets import QDialog

        canvas = mainframe.editor3d.editor

        part_id = mainframe.editor_db.editor.splices.GetSelection()

        if part_id is None:
            dlg = _part_search.SearchDialog(
                mainframe, _editor_db.SplicesPage, title='Add Splice',
                table=mainframe.global_db.splices_table)
            part_id = dlg.GetValue() if dlg.exec() == QDialog.DialogCode.Accepted else None
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
        interaction_type: "_interaction.MouseInteraction", clicked_object
    ) -> bool:
        """Forwards to an active add-session (see start_add); falls back
        to Base3D's own generic drag/rotation handling otherwise.
        """
        from ...add_handlers.editor_3d import splice as _add_splice  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_splice.Splice):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
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
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @_check_types.do
    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return SpliceMenu(self.mainframe.editor3d.editor, self)

    @property
    @_check_types.do
    def start_position(self):
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
    def branch_position(self):
        """Wire branch position (Point instance)"""
        return self._p3

    @property
    @_check_types.do
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2


class SpliceMenu(QMenu):
    """Represent a splice menu in :mod:`harness_designer.objects.objects_3d.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, canvas, selected):
        """Initialise the :class:`SpliceMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
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
    def on_add_wire(self):
        """Start the interactive wire placement flow, pinned to this
        splice's own branch point -- the part-search dialog (pre-filtered
        to wires whose diameter fits) opens immediately, straight into
        phase 1, same as a terminal's/cavity's own pinned Add Wire."""
        from PySide6.QtCore import QTimer
        from . import wire as _wire_3d

        mainframe = self.selected.mainframe
        splice_obj = self.selected.parent

        @_check_types.do
        def _do():
            _wire_3d.Wire.start_add(mainframe, splice=splice_obj)

        QTimer.singleShot(0, _do)

    @_check_types.do
    def on_trace_circuit(self):
        """Highlight every object on this splice's circuit."""
        _menu_ops.trace_circuit(self.selected)

    @_check_types.do
    def on_select(self):
        """Make this splice the active selection."""
        _menu_ops.select_object(self.selected)

    @_check_types.do
    def on_clone(self):
        """Arm clone mode using this splice as the template."""
        _menu_ops.clone_object(self.selected)

    @_check_types.do
    def on_delete(self):
        """Delete this splice from the project."""
        _menu_ops.delete_object(self.selected)

    @_check_types.do
    def on_properties(self):
        """Show this splice's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
