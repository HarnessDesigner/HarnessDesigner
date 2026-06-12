# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer

from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...ui.widgets import context_menus as _context_menus
from ...shapes import cylinder as _cylinder
from ...shapes import box as _box
from ...gl import materials as _materials
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import color as _color


if TYPE_CHECKING:
    from ...database.project_db import pjt_cavity as _pjt_cavity
    from .. import cavity as _cavity


class Cavity(_base3d.Base3D):
    """Represent a cavity in :mod:`harness_designer.objects.objects3d.cavity`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_cavity.Cavity" = None
    db_obj: "_pjt_cavity.PJTCavity" = None

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return CavityMenu(self.mainframe.editor3d.editor, self)

    def __init__(self, parent: "_cavity.Cavity",
                 db_obj: "_pjt_cavity.PJTCavity"):
        """Initialise the :class:`Cavity` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_cavity.Cavity`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_cavity.PJTCavity`
        """

        parent.mainframe.editor3d.context.acquire()
        self._part = db_obj.part
        scale = db_obj.part.scale
        angle = db_obj.part.angle3d
        position = db_obj.position3d
        material = _materials.Metallic(_color.Color(200, 200, 200, 75))

        if db_obj.part.round_terminal:
            vbo = _cylinder.create_vbo()
        else:
            vbo = _box.create_vbo()

        vbo.acquire()
        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)
        parent.mainframe.editor3d.context.release()

    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        terminal = self.db_obj.terminal
        if terminal is not None:
            delta = position - self._o_position
            t_position = terminal.position3d
            t_position += delta

        _base3d.Base3D._update_position(self, position)

    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        terminal = self.db_obj.terminal
        if terminal is not None:
            delta = angle - self._o_angle
            t_angle = terminal.angle3d
            t_angle += delta

        _base3d.Base3D._update_angle(self, angle)

    @property
    def seal_position(self) -> _point.Point:
        """Return the seal position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.db_obj.position3d


class CavityMenu(QMenu):
    """Represent a cavity menu in :mod:`harness_designer.objects.objects3d.cavity`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    def __init__(self, editor, obj):
        """Initialise the :class:`CavityMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param editor: Value for ``editor``.
        :type editor: UNKNOWN
        :param obj: Object instance to operate on.
        :type obj: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = editor
        self.selected = obj

        action = self.addAction('Add Terminal')
        action.triggered.connect(self.on_add_terminal)

        action = self.addAction('Add Seal')
        action.triggered.connect(self.on_add_seal)

        self.addSeparator()
        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    def on_add_terminal(self):
        """Add a terminal into this cavity."""
        def _do():
            from .. import terminal as _terminal_obj

            mainframe = self.selected.mainframe
            cavity = self.selected.db_obj

            try:
                compat_terminals = cavity.part.compat_terminals_array
            except AttributeError:
                compat_terminals = []

            part_id = _menu_ops.get_part_id(
                mainframe, 'terminals',
                mainframe.global_db.terminals_table, 'Add Terminal',
                initial_results=compat_terminals)

            if part_id is None:
                return

            position = cavity.position3d
            ptables = mainframe.project.ptables

            p3d = ptables.pjt_points3d_table.insert(*position.as_float)

            terminal_db = ptables.pjt_terminals_table.insert(
                part_id, None, p3d.db_id, cavity.db_id)

            terminal = _terminal_obj.Terminal(mainframe, terminal_db)
            mainframe.project.add_terminal(terminal)

        QTimer.singleShot(0, _do)

    def on_add_seal(self):
        """Attach a cavity plug seal to this cavity."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe
        cavity = self.selected.parent

        _menu_ops.run_attached_handler(
            lambda: _handlers.AddSealHandler(mainframe, cavity))

    def on_select(self):
        """Make this cavity the active selection."""
        _menu_ops.select_object(self.selected)

    def on_properties(self):
        """Show this cavity's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
