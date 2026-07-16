# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...ui.widgets import context_menus as _context_menus
from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config


if TYPE_CHECKING:
    from ...database.project_db import pjt_terminal as _pjt_terminal
    from .. import terminal as _terminal


Config = _config.Config.editor3d


class Terminal(_base3d.Base3D):
    """Represent a terminal in :mod:`harness_designer.objects.objects3d.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_terminal.Terminal" = None
    db_obj: "_pjt_terminal.PJTTerminal" = None

    def __init__(self, parent: "_terminal.Terminal",
                 db_obj: "_pjt_terminal.PJTTerminal"):
        """Initialise the :class:`Terminal` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_terminal.Terminal`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_terminal.PJTTerminal`
        """

        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part
        color = self._part.plating.color
        self._color = color.ui
        material = _materials.Polished(color.ui)

        model = self._part.model3d

        is_round = self._part.round_terminal

        if is_round:
            vbo = _cylinder.create_vbo()
        else:
            vbo = _box.create_vbo()

        scale = _point.Point(self._part.width, self._part.height, self._part.length)
        angle = db_obj.angle3d

        _base3d.Base3D.__init__(
            self, parent, db_obj, vbo, angle, db_obj.position3d,
            scale, material)

        # Cavity surface overlay (wire-side always, pin-side for
        # female/undetermined-gender terminals) — resolved lazily in
        # render() and cached until the owning cavity changes.
        self._overlay_cavity_id = None
        self._overlay_housing_3d = None
        self._overlay_cavity_obj = None
        self._overlay_wire_surf_idx: int = None
        self._overlay_pin_surf_idx: int = None

        parent.mainframe.editor3d.context.release()

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    def _refresh_overlay_state(self) -> None:
        """(Re)resolve which of the housing's mesh surfaces this terminal
        should overlay, and which wrapper object's selection state drives
        the overlay color.  Cheap no-op once the owning cavity stops
        changing between calls.
        """
        pjt_cavity = self.db_obj.cavity
        cavity_id = pjt_cavity.db_id if pjt_cavity is not None else None

        if cavity_id == self._overlay_cavity_id:
            return

        self._overlay_cavity_id = cavity_id
        self._overlay_housing_3d = None
        self._overlay_cavity_obj = None
        self._overlay_wire_surf_idx = None
        self._overlay_pin_surf_idx = None

        if pjt_cavity is None:
            return

        cavity_obj = pjt_cavity.get_object()
        if cavity_obj is None or cavity_obj.obj3d is None:
            return

        housing_pjt = pjt_cavity.housing
        housing_obj = housing_pjt.get_object() if housing_pjt is not None else None
        if housing_obj is None or housing_obj.obj3d is None:
            return

        self._overlay_cavity_obj = cavity_obj
        self._overlay_housing_3d = housing_obj.obj3d

        cavity_3d = cavity_obj.obj3d
        if cavity_3d.wire_surf_idx >= 0:
            self._overlay_wire_surf_idx = cavity_3d.wire_surf_idx

        if self._pin_overlay_needed(pjt_cavity) and cavity_3d.surf_idx >= 0:
            self._overlay_pin_surf_idx = cavity_3d.surf_idx

    def _pin_overlay_needed(self, pjt_cavity) -> bool:
        """Male terminals never show a pin-side overlay; female terminals
        always do; an undetermined gender defaults to showing it (terminal
        part gender checked first, then the housing's gender).
        """
        term_gender = (self._part.gender.name or '').strip().lower()
        if term_gender == 'male':
            return False
        if term_gender == 'female':
            return True

        housing_gender = (pjt_cavity.housing.part.gender.name or '').strip().lower()
        if housing_gender == 'male':
            return False

        return True

    def render(self, faces_program, edges_program, vertices_program):
        super().render(faces_program, edges_program, vertices_program)

        self._refresh_overlay_state()

        housing_3d = self._overlay_housing_3d
        if housing_3d is None:
            return

        cavity_obj = self._overlay_cavity_obj
        if cavity_obj is not None and cavity_obj.is_selected:
            color = self._selected_material.diffuse
        else:
            color = self._unselected_material.diffuse

        if self._overlay_wire_surf_idx is not None:
            housing_3d.render_surface_overlay(self._overlay_wire_surf_idx, color)

        if self._overlay_pin_surf_idx is not None:
            housing_3d.render_surface_overlay(self._overlay_pin_surf_idx, color)

    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        seal = self.db_obj.seal
        if seal is not None:
            delta = position - self._o_position
            t_position = seal.position3d
            t_position += delta

        _base3d.Base3D._update_position(self, position)

    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        seal = self.db_obj.seal
        if seal is not None:
            delta = angle - self._o_angle
            t_angle = seal.angle3d
            t_angle += delta

        _base3d.Base3D._update_angle(self, angle)

    @property
    def seal_position(self) -> _point.Point:
        """Return the seal position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.wire_position

    @property
    def wire_position(self) -> _point.Point:
        """Return the wire position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.wire_position3d

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return TerminalMenu(self.mainframe.editor3d.editor, self)


class TerminalMenu(QMenu):
    """Represent a terminal menu in :mod:`harness_designer.objects.objects3d.terminal`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`TerminalMenu` instance.

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

        action = self.addAction('Add Wire Service Loop')
        action.triggered.connect(self.on_add_wire_service_loop)

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        self.addSeparator()

        rotate_menu = _context_menus.Rotate3DMenu(canvas, selected.parent)
        self.addMenu(rotate_menu)

        mirror_menu = _context_menus.Mirror3DMenu(canvas, selected.parent)
        self.addMenu(mirror_menu)

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

    def on_add_wire(self):
        """Start the interactive wire placement flow from this terminal."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe

        def _factory():
            part_id = _menu_ops.get_part_id(
                mainframe, 'wires', mainframe.global_db.wires_table,
                'Add Wire')

            if part_id is None:
                return None

            return _handlers.AddWireHandler(mainframe, part_id)

        _menu_ops.start_handler(mainframe, _factory)

    def on_add_wire_service_loop(self):
        """Start the interactive wire service loop placement flow."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe

        def _factory():
            part_id = _menu_ops.get_part_id(
                mainframe, 'wires', mainframe.global_db.wires_table,
                'Add Wire Service Loop')

            if part_id is None:
                return None

            return _handlers.AddWireServiceLoopHandler(mainframe, part_id)

        _menu_ops.start_handler(mainframe, _factory)

    def on_add_seal(self):
        """Attach a seal to this terminal."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        terminal = self.selected.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddSealHandler(mainframe, terminal))

    def on_trace_circuit(self):
        """Highlight every object on this terminal's circuit."""
        _menu_ops.trace_circuit(self.selected)

    def on_select(self):
        """Make this terminal the active selection."""
        _menu_ops.select_object(self.selected)

    def on_clone(self):
        """Arm clone mode using this terminal as the template."""
        _menu_ops.clone_object(self.selected)

    def on_delete(self):
        """Delete this terminal from the project."""
        _menu_ops.delete_object(
            self.selected, self.selected.mainframe.project.delete_terminal)

    def on_properties(self):
        """Show this terminal's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
