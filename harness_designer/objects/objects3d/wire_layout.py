
from typing import TYPE_CHECKING

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from ... import gl_materials as _gl_materials
from ...shapes import sphere as _sphere
from ... import Config
from .mixins import move as _move_mixin


if TYPE_CHECKING:
    from ... import editor_3d as _editor_3d
    from ...database.project_db import pjt_wire3d_layout as _pjt_wire3d_layout


Config = Config.editor3d


class WireLayout(_base3d.Base3D, _move_mixin.MoveMixin):

    def __init__(self, editor3d: "_editor_3d.Editor3D", db_obj: "_pjt_wire3d_layout.PJTWire3DLayout"):

        super().__init__(editor3d)
        self._db_obj = db_obj

        self._position = db_obj.point3d.point
        self._o_position = self._position.copy()
        self._is_deleted = False
        self._is_dragging = False

        wires = db_obj.attached_wires

        wire = wires[-1]
        diameter = wire.part.od_mm

        self._diameter = diameter
        self._color = wire.part.color.ui
        self._material = _gl_materials.Plastic(self._color.rgba_scalar)

        vertices, faces = _sphere.create(float(diameter) / 2.0)
        tris, nrmls, count = self._get_triangles(vertices, faces)

        tris += self._position

        p1, p2 = self._compute_rect(tris)
        self._rect = [[p1, p2]]
        self._bb = [self._compute_bb(p1, p2)]

        self._triangles = [_base3d.TriangleRenderer([[tris, nrmls, count]], self._material)]

        self._position.bind(self._update_position)

        # Track bundle layout point we're synced to (by db_id, not strong reference)
        self._bundle_layout_point_id = None

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_wires:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)

    def set_diameter(self, parent_bundle, value: _decimal):
        vertices, faces = _sphere.create(float(value) / 2.0)
        tris, nrmls, count = self._get_triangles(vertices, faces)

        tris += self._position

        p1, p2 = self._compute_rect(tris)
        self._rect = [[p1, p2]]
        self._bb = [self._compute_bb(p1, p2)]

        self._triangles[0].data = [[tris, nrmls, count]]

        for bundle in self.editor3d.mainframe.project.bundles:
            if (
                bundle.obj3d.position.db_id == self.position.db_id and
                parent_bundle != bundle.obj3d
            ):
                bundle.obj3d.set_diameter(self, value)
                break

    @property
    def is_dragging(self) -> bool:
        return self._is_dragging

    @is_dragging.setter
    def is_dragging(self, value: bool):
        self._is_dragging = value

        for bundle in self.editor3d.mainframe.project.bundles:
            if bundle.obj3d.position.db_id == self.position.db_id:
                bundle.obj3d.is_dragging = value

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
            bundle_layout_point = _point.Point(_decimal(0), _decimal(0), _decimal(0),
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
