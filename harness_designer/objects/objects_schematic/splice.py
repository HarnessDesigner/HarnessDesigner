# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from . import base_schematic as _base_schematic
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...shapes import sphere as _sphere
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database.project_db import pjt_splice as _pjt_splice
    from .. import splice as _splice


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
