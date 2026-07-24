# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math
from PySide6.QtWidgets import QMenu
import build123d

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import cylinder as _cylinder
from ...gl import vbo as _vbo
from ...gl import materials as _materials
from ... import config as _config
from ... import utils as _utils


if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice


Config = _config.Config.editor3d


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


class Splice(_base3d.Base3D):
    """Represent a splice in :mod:`harness_designer.objects.objects3d.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_splice.Splice" = None
    db_obj: "_pjt_splice.PJTSplice" = None

    def __init__(self, parent: "_splice.Splice",
                 db_obj: "_pjt_splice.PJTSplice"):
        """Initialise the :class:`Splice` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_splice.Splice`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_splice.PJTSplice`
        """

        parent.mainframe.editor3d.context.acquire()

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

        _base3d.Base3D.__init__(
            self, parent, db_obj, vbo, angle, position,
            scale, material)

        parent.mainframe.editor3d.context.release()

        if model is not None:
            model.load(self._part.manufacturer.name,
                       self._part.part_number, self._set_model)

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return SpliceMenu(self.mainframe.editor3d.editor, self)

    @property
    def start_position(self):
        """Wire start position (Point instance)"""
        return self._p1

    @property
    def wire_position(self) -> _point.Point:
        """Return the wire position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.branch_position

    @property
    def branch_position(self):
        """Wire branch position (Point instance)"""
        return self._p3

    @property
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2


class SpliceMenu(QMenu):
    """Represent a splice menu in :mod:`harness_designer.objects.objects3d.splice`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

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

    def on_add_wire(self):
        """Start the interactive wire placement flow from this splice."""
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

    def on_trace_circuit(self):
        """Highlight every object on this splice's circuit."""
        _menu_ops.trace_circuit(self.selected)

    def on_select(self):
        """Make this splice the active selection."""
        _menu_ops.select_object(self.selected)

    def on_clone(self):
        """Arm clone mode using this splice as the template."""
        _menu_ops.clone_object(self.selected)

    def on_delete(self):
        """Delete this splice from the project."""
        _menu_ops.delete_object(self.selected)

    def on_properties(self):
        """Show this splice's properties in the object editor."""
        _menu_ops.show_properties(self.selected)
