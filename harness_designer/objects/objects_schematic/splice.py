# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from . import base_schematic as _base_schematic
from ...geometry import angle as _angle
from ...geometry import point as _point
from ...gl.canvas_base import interaction as _interaction
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...shapes import sphere as _sphere
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice
    from .. import wire as _wire_facade
    from ... import ui as _ui


Config = _config.Config.editor_schematic


class Splice(_base_schematic.BaseSchematic):
    """
    2D representation of a splice for schematic view

    Renders as the same shared ``shapes/sphere.py`` mesh -- the
    ``schematic2d`` shader already does the full 3D lighting/transform
    before projecting to 2D, so a real sphere (rather than a flat disc)
    costs nothing extra and shades correctly -- on the VBO/shader
    pipeline (see ``objects_schematic/base_schematic.py``'s ``BaseSchematic``), matching how
    ``Base3D`` subclasses render.
    """
    _parent: "_splice.Splice"
    db_obj: "_pjt_splice.PJTSplice"

    @_check_types.do
    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):
        """Initialise the :class:`Splice` instance.

        :param parent: Parent object.
        :type parent: :class:`_splice.Splice`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """
        position = db_obj.position2d

        # PJTSplice has Position2DMixin but no angle2d mixin -- a sphere
        # is rotationally symmetric so the value never matters visually,
        # but BaseVar._compute_obb/_compute_aabb both bail out entirely
        # when self._angle is None, which would leave this splice
        # permanently unpickable. A static, unbound identity Angle (not
        # DB-backed -- there's no column to bind to) gives that math a
        # real rotation to use -- same fix objects_schematic/wire_layout.py's
        # WireLayout already uses for the same reason.
        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        diameter = Config.object_sizes.splice.diameter
        scale = _point.Point(diameter, diameter, diameter)
        material = _materials.Generic(_color.Color(*Config.colors.splice))

        with parent.mainframe.editor2d.editor.context:
            vbo = _sphere.create_vbo()
            super().__init__(parent, db_obj, vbo, angle, position, scale, material)

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

    @classmethod
    @_check_types.do
    def start_add(
        cls, mainframe: "_ui.MainFrame", wire: "_wire_facade.Wire | None" = None
    ) -> "_splice.Splice | None":
        """Wire-snapping splice placement, schematic-native -- see
        add_handlers.editor_schematic.splice's own module docstring for
        how the cut position is derived. Mirrors
        objects_3d.splice.Splice.start_add's own two-entry-mode shape
        (given *wire* locks immediately; otherwise waits for the first
        hover over a compatible wire).
        """
        from ...handlers import splice_handler as _splice_handler
        from ...ui.dialogs import part_search as _part_search
        from ...ui import editor_db as _editor_db
        from ...add_handlers.editor_schematic import splice as _add_splice
        from .. import splice as _splice_facade
        from PySide6.QtWidgets import QDialog

        canvas = mainframe.editor2d.editor

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

        preview_material = _materials.Generic(
            _color.Color(*_config.Config.colors.add_object.preview_color))
        compat_material = _materials.Generic(
            _color.Color(*_config.Config.colors.add_object.wire_highlight))

        for w in mainframe.project.wires:
            if _splice_handler._wire_fits(part, w):  # NOQA
                w.identify(compat_material)

        half = float(part.length) / 2.0
        start_db = ptables.pjt_points3d_table.insert(0.0, 0.0, -half)
        stop_db = ptables.pjt_points3d_table.insert(0.0, 0.0, half)
        branch_db = ptables.pjt_points3d_table.insert(0.0, 0.0, 0.0)
        point2d_db = ptables.pjt_points2d_table.insert(0.0, 0.0)

        name = f'{part.manufacturer.name} {part.part_number}'

        db_obj = ptables.pjt_splices_table.insert(
            part_id, name, start_db.db_id, stop_db.db_id, branch_db.db_id,
            point2d_db.db_id, None)

        facade = _splice_facade.Splice(mainframe, db_obj)
        facade.identify(preview_material)
        facade.objschematic.is_visible = False

        handler = _add_splice.Splice(
            canvas, facade, part_id, part, preview_material, compat_material)

        facade.objschematic._active_handler = handler  # NOQA
        canvas.active_handler_obj = facade.objschematic

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
        to BaseSchematic's own generic drag handling otherwise.
        """
        from ...add_handlers.editor_schematic import splice as _add_splice  # NOQA -- avoid a cycle at import time

        if isinstance(self._active_handler, _add_splice.Splice):
            handled = self._active_handler(
                last_pos, current_pos, had_motion, interaction_type, clicked_object)

            if self._active_handler.is_finished:
                self._active_handler = None

            return handled

        return super().handle_interaction(
            last_pos, current_pos, had_motion, interaction_type, clicked_object)


class SpliceMenu(QMenu):
    """Represent a splice menu in :mod:`harness_designer.objects.objects_schematic.splice`.

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
        """Handle the add wire event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_trace_circuit(self):
        """Handle the trace circuit event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_clone(self):
        """Handle the clone event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    @_check_types.do
    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
