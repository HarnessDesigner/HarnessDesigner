from typing import TYPE_CHECKING
import weakref

import build123d

from ...geometry import point as _point
from ...geometry import line as _line
from ...geometry import angle as _angle
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D


if TYPE_CHECKING:
    from ... import editor3d as _editor3d
    from ...database.project_db import pjt_bundle as _pjt_bundle


def _build_model(p1: _point.Point, p2: _point.Point, diameter: _decimal):
    line = _line.Line(p1, p2)
    wire_length = line.length()
    wire_radius = diameter / _decimal(2.0)

    # Create the bundle cylinder
    model = build123d.Cylinder(float(wire_radius), float(wire_length), align=build123d.Align.NONE)

    bb = model.bounding_box()

    corner1 = _point.Point(*[_decimal(item) for item in bb.min])
    corner2 = _point.Point(*[_decimal(item) for item in bb.max])

    return model, (corner1, corner2)


class Bundle(_Base3D):
    """Bundle represents a group of wires bundled together.
    
    Bundles are dynamic aggregates:
    - Wires hold strong references to bundles as a sanity check
    - Bundles and bundle layouts are not stored strongly in the UI frame container
    - Bundle length is initially derived from wire layouts on creation
    - Then controlled by bundle layout points
    - Moving bundle layouts updates wire layout points and thus wire lengths
    """

    def __init__(self, editor3d: "_editor3d.Editor3D", db_obj: "_pjt_bundle.PJTBundle"):
        super().__init__(editor3d)
        self._db_obj = db_obj
        self._part = db_obj.part

        self._p1 = db_obj.start_point.point
        self._p2 = db_obj.stop_point.point

        self._model = None
        self._hit_test_rect = None

        self._triangles = []
        
        # Track wires in this bundle using weak references
        # Wires hold strong references to bundles; bundles use weak refs to wires
        self._wires = []  # List of weak references to Wire objects

        self._p1.Bind(self.recalculate)
        self._p2.Bind(self.recalculate)
    
    def add_wire(self, wire):
        """Add a wire to this bundle.
        
        Wires in a bundle are not rendered (is_visible=False).
        Uses weak reference to avoid circular reference issues.
        """
        # Store weak reference to the wire
        wire_ref = weakref.ref(wire, self._on_wire_deleted)
        self._wires.append(wire_ref)
        
        # Hide the wire when it's bundled
        wire.is_visible = False
    
    def remove_wire(self, wire):
        """Remove a wire from this bundle.
        
        Makes the wire visible again.
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

    def recalculate(self, *_):
        if self._is_deleted:
            return

        (
            self._model,
            self._hit_test_rect
        ) = _build_model(self._p1, self._p2, self._part.od_mm)

        angle = _angle.Angle(self._p1, self._p2)
        p1, p2 = self._hit_test_rect
        p2 @= angle

        p1 += self._p1
        p2 += self._p1

    def hit_test(self, point: _point.Point) -> bool:
        if self._is_deleted:
            return False

        if self._hit_test_rect is None:
            return False

        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
        if self._is_deleted:
            return

        if not self._triangles:
            angle = _angle.Angle(self._p1, self._p2)
            normals, verts, count = renderer.build_mesh(self._model)

            verts @= angle
            verts += self._p1

            self._triangles = [[normals, verts, count]]

        for normals, verts, count in self._triangles:
            renderer.model(normals, verts, count, None, self._part.color.ui.rgb_scalar, self.is_selected)
    
    def delete(self):
        """Override delete to restore wire visibility."""
        # Restore visibility of all wires before deleting
        for ref in self._wires[:]:
            wire = ref()
            if wire is not None:
                wire.is_visible = True
        self._wires.clear()
        super().delete()

