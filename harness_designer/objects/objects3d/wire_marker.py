# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu
from PySide6.QtCore import QTimer

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils
from ... import color as _color


if TYPE_CHECKING:
    from .. import wire_marker as _wire_marker
    from ...database.project_db import pjt_wire_marker as _pjt_wire_marker


Config = _config.Config.editor3d


class WireMarker(_base3d.Base3D):
    """Represent a wire marker in :mod:`harness_designer.objects.objects3d.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_wire_marker.WireMarker" = None
    db_obj: "_pjt_wire_marker.PJTWireMarker" = None

    def __init__(self, parent: "_wire_marker.WireMarker",
                 db_obj: "_pjt_wire_marker.PJTWireMarker"):
        """Initialise the :class:`WireMarker` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire_marker.WireMarker`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_marker.PJTWireMarker`
        """

        parent.mainframe.editor3d.context.acquire()

        self._part = db_obj.part
        position = db_obj.position3d
        wire = db_obj.wire
        wire_p1 = wire.start_position3d
        wire_p2 = wire.stop_position3d

        p1_distance = _line.Line(wire_p1, position).length()
        p2_distance = _line.Line(wire_p2, position).length()

        if p1_distance > p2_distance:
            self._distance = p1_distance
        else:
            self._distance = p2_distance
            wire_p1, wire_p2 = wire_p2, wire_p1

        angle = _angle.Angle.from_points(wire_p1, wire_p2)

        color = db_obj.part.color.ui
        material = _materials.Plastic(color)

        color = _color.Color(0.05, 0.05, 0.05, 1.0)

        length = 5.0
        diameter = wire.part.od_mm + 0.05
        scale = _point.Point(diameter, diameter, length)
        vbo = _cylinder.create_vbo()

        label_material = _materials.Plastic(color)
        self._p1 = wire_p1
        self._p2 = wire_p2

        wire_p1.bind(self._update_position)
        wire_p2.bind(self._update_position)

        vbo.acquire()
        _base3d.Base3D.__init__(
            self, parent, db_obj, vbo, angle, db_obj.position3d, scale, material)

        parent.mainframe.editor3d.context.release()


    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        if position.db_id == self._position.db_id:
            line = _line.Line(self._p1, self._p2)

            new_position = line.project_to_line(position)

            delta = new_position - position
            with position:
                position += delta

            self._o_position = position.copy()

        else:
            inverse_angle = -self._angle
            position = self._position.copy()

            position -= self._p1
            position @= inverse_angle

            angle = _angle.Angle.from_points(self._p1, self._p2)
            self._angle._q = angle._q  # NOQA

            position @= self._angle
            position += self._p1

            delta = position - self._position
            with self._position:
                self._position += delta

            self._o_position = self._position.copy()

        self._compute_obb()
        self._compute_aabb()

        self.editor3d.update()

    def flip(self):
        """Flip the marker so the label reads in the opposite direction."""
        self._p1, self._p2 = self._p2, self._p1

        angle = _angle.Angle.from_points(self._p1, self._p2)
        self._angle._q = angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

        self.editor3d.Refresh()

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireMarkerMenu(self.mainframe.editor3d.editor, self)


class WireMarkerMenu(QMenu):
    """Represent a wire marker menu in :mod:`harness_designer.objects.objects3d.wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`WireMarkerMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Set Label')
        action.triggered.connect(self.on_set_label)

        action = self.addAction('Flip Label')
        action.triggered.connect(self.on_flip_label)

        self.addSeparator()

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

    def on_set_label(self):
        """Edit the marker label."""
        def _do():
            from PySide6.QtWidgets import QInputDialog

            mainframe = self.selected.mainframe
            current = self.selected.db_obj.label or ''

            label, ok = QInputDialog.getText(
                mainframe, 'Set Label', 'Label:', text=current)

            if not ok or label == current:
                return

            self.selected.db_obj.label = label
            self.selected.editor3d.Refresh()

        QTimer.singleShot(0, _do)

    def on_flip_label(self):
        """Flip the marker label so it reads in the opposite direction."""
        self.selected.flip()

    def on_select(self):
        """Make this wire marker the active selection."""
        _menu_ops.select_object(self.selected)

    def on_clone(self):
        """Arm clone mode using this wire marker as the template."""
        _menu_ops.clone_object(self.selected)

    def on_delete(self):
        """Delete this wire marker from the project."""
        _menu_ops.delete_object(
            self.selected, self.selected.mainframe.project.delete_wire_marker)

    def on_properties(self):
        """Show this wire marker's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
