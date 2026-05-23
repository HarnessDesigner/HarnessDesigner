# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import weakref
from PySide6.QtWidgets import QMenu
import math
import numpy as np

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from . import base3d as _base3d
from ...shapes import cylinder as _cylinder
from ... import config as _config
from ...gl import materials as _materials


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle as _pjt_bundle
    from .. import bundle as _bundle


Config = _config.Config.editor3d


class Bundle(_base3d.Base3D):
    """Represent a bundle in :mod:`harness_designer.objects.objects3d.bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    parent: "_bundle.Bundle" = None
    db_obj: "_pjt_bundle.PJTBundle" = None

    def __init__(self, parent: "_bundle.Bundle",
                 db_obj: "_pjt_bundle.PJTBundle"):
        """Initialise the :class:`Bundle` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: :class:`_bundle.Bundle`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_bundle.PJTBundle`
        """

        parent.mainframe.editor3d.context.acquire()
        self._part = db_obj.part

        layers = db_obj.concentric.layers
        if layers:
            self._diameter = layers[-1].diameter
        else:
            self._diameter = self._part.min_size

        color = self._part.color.ui
        material = _materials.Rubber(color)

        start_layout = db_obj.start_layout
        stop_layout = db_obj.stop_layout

        self._is_start_clickable = start_layout is None
        self._is_stop_clickable = stop_layout is None

        self._p1 = db_obj.start_position3d
        self._p2 = db_obj.stop_position3d

        position = self._p1
        angle = _angle.Angle()
        scale = _point.Point(self._diameter, self._diameter, 0.0)
        vbo = _cylinder.create_vbo()
        vbo.acquire()

        _base3d.Base3D.__init__(self, parent, db_obj, vbo, angle, position, scale, material)

        # Track wires in this bundle using weak references
        # Wires hold strong references to bundles; bundles use weak refs to wires
        self._wires = []  # List of weak references to Wire objects

        self._p2.bind(self._update_position)
        self._update_position(None)
        parent.mainframe.editor3d.context.release()

    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        pass

    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        self._update_position(None)

    def _update_position(self, _: _point.Point):
        """Calculate position, rotation, and scale from endpoints"""

        # Calculate wire vector
        wire_vector = (self._p1 - self._p2).as_numpy
        length = np.linalg.norm(wire_vector)

        if length < 0.001:
            length = 0.001  # Prevent zero length

        self._scale.z = length

        direction = wire_vector / length

        # Rotation: align +Z axis with wire direction
        new_angle = self._rotation_from_direction(direction)
        self._angle._q = new_angle._q  # NOQA

        self._compute_obb()
        self._compute_aabb()

    @staticmethod
    def _rotation_from_direction(direction):
        """Create quaternion to rotate +Z axis to align with direction"""
        # Unit cylinder points along +Z, rotate it to point along 'direction'
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)

        # Handle special case: direction already aligned with Z
        dot = np.dot(z_axis, direction)
        if abs(dot - 1.0) < 0.0001:
            return _angle.Angle.from_quat([1.0, 0.0, 0.0, 0.0])  # Identity
        if abs(dot + 1.0) < 0.0001:
            # 180 degree rotation around X axis
            return _angle.Angle.from_quat([0.0, 1.0, 0.0, 0.0])

        # Calculate rotation axis and angle
        axis = np.cross(z_axis, direction)  # NOQA
        axis = axis / np.linalg.norm(axis)

        angle = math.acos(np.clip(dot, -1.0, 1.0))

        return _angle.Angle.from_axis_angle(axis, angle)

    def set_diameter(self, parent_layout, value: float):
        """Set the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent_layout: Value for ``parent_layout``.
        :type parent_layout: UNKNOWN
        :param value: Value to store or process.
        :type value: float
        """
        # TODO: set transition branch diameter
        #       finish code to cascade bundle diameter
        #       through layouts from one end of the bundle to the other stopping
        #       at a boot, the end of the bundle or a transition branch
        self._diameter = value
        self._scale.x = value
        self._scale.y = value

        if parent_layout.position.db_id == self._p1.db_id:
            for layout in self.editor3d.mainframe.project.bundle_layouts:
                if layout.obj3d.position.db_id == self._p2.db_id:
                    layout.obj3d.set_diameter(self, value)
                    break
            else:
                for transition in self.editor3d.mainframe.project.transitions:
                    index = transition.obj3d.get_branch_index(self._p2)

        else:
            for layout in self.editor3d.mainframe.project.bundle_layouts:
                if layout.obj3d.position.db_id == self._p1.db_id:
                    layout.obj3d.set_diameter(self, value)
                    break

    def add_wire(self, wire):
        """Add a wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param wire: Value for ``wire``.
        :type wire: UNKNOWN
        """
        # Store weak reference to the wire
        wire_ref = weakref.ref(wire, self._on_wire_deleted)
        self._wires.append(wire_ref)

        # Hide the wire when it's bundled
        if wire.is_visible:
            wire.is_visible = False

    def remove_wire(self, wire):
        """Remove the wire.

        UNKNOWN details are inferred from the callable name and signature.

        :param wire: Value for ``wire``.
        :type wire: UNKNOWN
        """
        # Remove the weak reference
        for ref in self._wires[:]:
            w = ref()
            if w is None:
                self._wires.remove(ref)
            elif w == wire:
                self._wires.remove(ref)
                # Make the wire visible again
                wire.is_visible = True
                break

    def _on_wire_deleted(self, ref):
        """Callback when a wire is garbage collected."""
        if ref in self._wires:
            self._wires.remove(ref)

    @property
    def wires(self):
        """Get all wires in this bundle (that still exist)."""
        for ref in self._wires[:]:
            wire = ref()
            if wire is None:
                self._wires.remove(ref)
            else:
                yield wire

    @property
    def wire_count(self) -> int:
        """Return the number of wires in this bundle."""
        count = 0
        for ref in self._wires[:]:
            if ref() is None:
                self._wires.remove(ref)
            else:
                count += 1

        return count

    def delete(self):
        """Override delete to restore wire visibility."""
        # Restore visibility of all wires before deleting
        for ref in self._wires[:]:
            wire = ref()
            if wire is not None:
                wire.is_visible = True

        self._wires.clear()
        super().delete()

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return BundleMenu(self.mainframe.editor3d.editor, self)

    @property
    def start_position(self):
        """Wire start position (Point instance)"""
        return self._p1

    @property
    def stop_position(self):
        """Wire stop position (Point instance)"""
        return self._p2


class BundleMenu(QMenu):
    """Represent a bundle menu in :mod:`harness_designer.objects.objects3d.bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, canvas, selected):
        """Initialise the :class:`BundleMenu` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param canvas: Canvas instance.
        :type canvas: UNKNOWN
        :param selected: Value for ``selected``.
        :type selected: UNKNOWN
        """
        QMenu.__init__(self)
        self.canvas = canvas
        self.selected = selected

        action = self.addAction('Add Handle')
        action.triggered.connect(self.on_add_handle)

        action = self.addAction('Add Transition')
        action.triggered.connect(self.on_add_transition)

        self.addSeparator()
        action = self.addAction('Select')
        action.triggered.connect(self.on_select)

        self.addSeparator()
        action = self.addAction('Delete')
        action.triggered.connect(self.on_delete)

        self.addSeparator()
        action = self.addAction('Properties')
        action.triggered.connect(self.on_properties)

    def on_add_handle(self):
        """Handle the add handle event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass

    def on_add_transition(self):
        """Handle the add transition event.

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

    def on_properties(self):
        """Handle the properties event.

        UNKNOWN details are inferred from the callable name and signature.
        """
        pass
