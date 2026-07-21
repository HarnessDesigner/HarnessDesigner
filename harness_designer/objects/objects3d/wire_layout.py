# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMenu

from ...geometry import point as _point
from ...geometry import angle as _angle
from . import base3d as _base3d
from . import menu_ops as _menu_ops
from ...shapes import sphere as _sphere
from ...gl import materials as _materials
from ... import config as _config
from ... import color as _color


if TYPE_CHECKING:
    from ...database.project_db import pjt_wire_layout as _pjt_wire_layout
    from .. import wire_layout as _wire_layout


Config = _config.Config.editor3d


class WireLayout(_base3d.Base3D):
    """Represent a wire layout in :mod:`harness_designer.objects.objects3d.wire_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_wire_layout.WireLayout" = None
    db_obj: "_pjt_wire_layout.PJTWireLayout" = None

    # Sits on the wire's centerline, inside its OBB by design -- see
    # Base3D._pick_priority.
    _pick_priority = 1

    def __init__(self, parent: "_wire_layout.WireLayout",
                 db_obj: "_pjt_wire_layout.PJTWireLayout"):
        """Initialise the :class:`WireLayout` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_wire_layout.WireLayout`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_wire_layout.PJTWireLayout`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """

        parent.mainframe.editor3d.context.acquire()

        self._bundle_layout_point_id = None

        wires = db_obj.attached_wires
        if wires:
            diameter = wires[0].part.od_mm
            color = wires[0].part.color.ui
        else:
            diameter = 3.0
            color = _color.Color(0.5, 0.5, 0.5, 1.0)

        material = _materials.Plastic(color)

        scale = _point.Point(diameter, diameter, diameter)
        vbo = _sphere.create_vbo()
        angle = _angle.Angle()
        position = db_obj.position3d
        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)
        parent.mainframe.editor3d.context.release()

    @property
    def wire_position(self) -> _point.Point:
        """Return the wire position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self.position

    def _sync_from_bundle_layout_point(self, point: _point.Point):
        """Callback to sync wire layout point position from bundle layout point.

        This is called when the bundle layout point moves. Wire layout points
        share coordinates with bundle layout points but do NOT share the same
        Point instances.
        """
        if self._is_deleted:
            return

        # Update our center to match the bundle layout point
        delta = point - self._position
        self._position += delta

    def bind_to_bundle_layout_point(self, bundle_layout_point: _point.Point):
        """Register callback to bundle layout point for synchronization.

        When a wire is bundled, wire layouts register callbacks to the relevant
        bundle layout Points so wires follow bundle movement.
        """
        if self._bundle_layout_point_id is not None:
            # Already bound, unbind first
            self.unbind_from_bundle_layout_point()

        # Store the db_id for tracking (not a strong reference)
        self._bundle_layout_point_id = bundle_layout_point.db_id

        # Bind our sync callback to the bundle layout point
        bundle_layout_point.bind(self._sync_from_bundle_layout_point)

        # Initial sync
        self._sync_from_bundle_layout_point(bundle_layout_point)

    def unbind_from_bundle_layout_point(self):
        """Unbind from bundle layout point.

        When a wire is unbundled, wire layouts unbind themselves from the
        bundle layout Points.
        """
        if self._bundle_layout_point_id is None:
            return

        # Use db_id-based lookup to get the point without holding strong reference
        # The PointMeta cache will return the same instance if it still exists
        try:
            bundle_layout_point = _point.Point(0.0, 0.0, 0.0,
                                               db_id=self._bundle_layout_point_id)

            bundle_layout_point.unbind(self._sync_from_bundle_layout_point)

        except:  # NOQA
            # Point may have been garbage collected
            pass

        self._bundle_layout_point_id = None

    def delete(self):
        """Override delete to clean up bundle bindings."""
        self.unbind_from_bundle_layout_point()
        super().delete()

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return WireLayoutMenu(self.mainframe.editor3d.editor, self)


class WireLayoutMenu(QMenu):
    """Represent a wire layout menu in :mod:`harness_designer.objects.objects3d.wire_layout`.

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
        """Start the interactive splice placement flow."""
        from ... import handlers as _handlers

        mainframe = self.selected.mainframe

        _menu_ops.start_handler(
            mainframe, lambda: _handlers.AddSpliceHandler(mainframe))

    def on_trace_circuit(self):
        """Highlight every object on the circuit of an attached wire."""
        wires = self.selected.db_obj.attached_wires

        if wires:
            _menu_ops.trace_circuit(self.selected, wires[0])

    def on_select(self):
        """Make this wire layout the active selection."""
        _menu_ops.select_object(self.selected)

    def on_delete(self):
        """Delete this wire layout from the project."""
        _menu_ops.delete_object(
            self.selected, self.selected.mainframe.project.delete_wire_layout)
