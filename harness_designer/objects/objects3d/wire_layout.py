from typing import TYPE_CHECKING, Union


import build123d

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from . import Base3D as _Base3D

if TYPE_CHECKING:
    from ... import editor3d as _editor3d
    from ...database.project_db import pjt_wire3d_layout as _pjt_wire3d_layout


def _build_model(diameter: _decimal):
    model = build123d.Sphere(float(diameter / _decimal(2)))

    bbox = model.bounding_box()
    corner1 = _point.Point(*(_decimal(float(item)) for item in bbox.min))
    corner2 = _point.Point(*(_decimal(float(item)) for item in bbox.max))

    return model, [corner1, corner2]


class WireLayout(_Base3D):

    def __init__(self, editor3d: "_editor3d.Editor3D",
                 db_obj: "_pjt_wire3d_layout.PJTWire3DLayout"):

        super().__init__(editor3d)
        self._db_obj = db_obj

        self._center = db_obj.point.point
        self._o_center = self._center.copy()
        self._model = None
        self._hit_test_rect = None
        self._triangles = []
        
        # Track bundle layout point we're synced to (by db_id, not strong reference)
        self._bundle_layout_point_id = None

        self._center.Bind(self._update_center)

    def _update_center(self, *_):
        if self._is_deleted:
            return

        if self._triangles:
            verts = self._triangles[0][1]
            center_diff = self._center - self._o_center
            verts += center_diff

        if self._hit_test_rect is not None:
            p1, p2 = self._hit_test_rect

            center_diff = self._center - self._o_center
            p1 += center_diff
            p2 += center_diff

        self._o_center = self._center.copy()
    
    def _sync_from_bundle_layout_point(self, bundle_point: _point.Point):
        """Callback to sync wire layout point position from bundle layout point.
        
        This is called when the bundle layout point moves. Wire layout points
        share coordinates with bundle layout points but do NOT share the same
        Point instances.
        """
        if self._is_deleted:
            return
        
        # Update our center to match the bundle layout point
        with self._center:
            self._center.x = bundle_point.x
            self._center.y = bundle_point.y
            self._center.z = bundle_point.z
    
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
            bundle_layout_point = _point.Point._instances.get(self._bundle_layout_point_id)
            if bundle_layout_point is not None:
                bundle_layout_point.unbind(self._sync_from_bundle_layout_point)
        except:  # NOQA
            # Point may have been garbage collected
            pass
        
        self._bundle_layout_point_id = None

    def recalculate(self, *_):
        if self._is_deleted:
            return

        if self._model is None:
            self._model, self._hit_test_rect = _build_model(self._db_obj.diameter)

            p1, p2 = self._hit_test_rect
            p1 += self._center
            p2 += self._center

        self._triangles = []

    def hit_test(self, point: _point.Point) -> bool:
        if self._is_deleted:
            return False

        p1, p2 = self._hit_test_rect
        return p1 <= point <= p2

    def draw(self, renderer):
        if self._is_deleted:
            return

        if not self._triangles:
            normals, verts, count = renderer.build_mesh(self._model)
            verts += self._center

            self._triangles = [[normals, verts, count]]

        for normals, verts, count in self._triangles:
            color = (0.2, 0.2, 0.2, 1.0)
            for obj in self._db_obj.attached_objects:
                color = obj.part.color.ui.rgba_scalar
                break

            renderer.model(normals, verts, count, None, color, self.is_selected)
    
    def delete(self):
        """Override delete to clean up bundle bindings."""
        self.unbind_from_bundle_layout_point()
        super().delete()
