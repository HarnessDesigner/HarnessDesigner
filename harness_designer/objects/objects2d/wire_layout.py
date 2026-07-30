# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from . import base2d as _base2d
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import config as _config
from ... import color as _color
from ...gl import materials as _materials
from ...shapes import sphere as _sphere


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_layout as _pjt_wire_layout
    from .. import wire_layout as _wire_layout


Config = _config.Config.editor2d


class WireLayout(_base2d.Base2D):
    """
    2D representation of a wire layout (drag handle) for schematic view

    Renders as the same shared ``shapes/sphere.py`` mesh
    ``objects3d/wire_layout.py``'s ``WireLayout`` uses -- the
    ``schematic2d`` shader already does the full 3D lighting/transform
    before projecting to 2D, so there's no need for a flat-only mesh
    here -- on the VBO/shader pipeline (see ``objects2d/base2d.py``'s
    ``Base2D``). Colored to match its attached wire, sized at a fixed
    ``Config.editor2d.wire_layout.diameter`` (rather than the wire's
    real ``od_mm`` like the 3D editor) so it stays comfortably larger
    than the fixed-width 2D wire regardless of gauge.
    """
    _parent: "_wire_layout.WireLayout" = None
    db_obj: "_pjt_wire_layout.PJTWireLayout"

    # Sits on the wire's own centerline/OBB by design -- see
    # objects.objectsvar.base_var.BaseVar._pick_priority.
    _pick_priority = 1

    def __init__(self, parent: "_wire_layout.WireLayout",
                 db_obj: "_pjt_wire_layout.PJTWireLayout"):
        """Initialise the :class:`WireLayout` instance.

        :param parent: Parent object.
        :type parent: :class:`_wire_layout.WireLayout`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_layout.PJTWireLayout`
        """
        position = db_obj.position2d

        # PJTWireLayout has Position2DMixin but no angle2d mixin -- a
        # sphere is rotationally symmetric so the value never matters
        # visually, but BaseVar._compute_obb/_compute_aabb both bail out
        # entirely when self._angle is None, which would leave this
        # handle permanently unpickable. A static, unbound identity
        # Angle (not DB-backed -- there's no column to bind to) gives
        # that math a real rotation to use -- same fix
        # objects2d/splice.py's Splice uses for the same reason.
        angle = _angle.Angle.from_euler(0.0, 0.0, 0.0)

        wires = db_obj.attached_wires
        color = wires[0].part.color.ui if wires else _color.Color(0.5, 0.5, 0.5, 1.0)
        material = _materials.Generic(color)

        diameter = Config.wire_layout.diameter
        scale = _point.Point(diameter, diameter, diameter)

        with parent.mainframe.editor2d.editor.context:
            vbo = _sphere.create_vbo()
            super().__init__(parent, db_obj, vbo, angle, position, scale, material)


class WireLayoutMenu(QMenu):
    """Represent a wire layout menu in :mod:`harness_designer.objects.objects2d.wire_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`WireLayoutMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Splice')
        action.triggered.connect(self.on_add_splice)

        self.addSeparator()
        action = self.addAction('Trace Circuit')
        action.triggered.connect(self.on_trace_circuit)

        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

    def on_add_splice(self):
        """Handle the add splice event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_trace_circuit(self):
        """Handle the trace circuit event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_select(self):
        """Handle the select event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_delete(self):
        """Handle the delete event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
