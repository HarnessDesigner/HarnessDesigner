
from typing import TYPE_CHECKING


import build123d

from ...geometry import point as _point
from ...wrappers.decimal import Decimal as _decimal
from . import base3d as _base3d
from ... import gl_materials as _gl_materials
from ...shapes import sphere as _sphere
from ... import Config
from .mixins import move as _move_mixin


if TYPE_CHECKING:
    from ...database.project_db import pjt_bundle_layout as _pjt_bundle_layout
    from .. import bundle_layout as _bundle_layout


Config = Config.editor3d


class BundleLayout(_base3d.Base3D, _move_mixin.MoveMixin):
    _parent: "_bundle_layout.BundleLayout" = None

    def __init__(self, parent: "_bundle_layout.BundleLayout",
                 db_obj: "_pjt_bundle_layout.PJTBundleLayout"):

        _base3d.Base3D.__init__(self, parent)
        self._db_obj: "_pjt_bundle_layout.PJTBundleLayout" = db_obj

        self._position = db_obj.point3d.point
        self._o_position = self._position.copy()
        self._is_deleted = False
        self._is_dragging = False

        bundles = db_obj.attached_bundles

        bundle = bundles[-1]
        layers = bundle.concentric.layers
        diameter = layers[-1].diameter

        self._diameter = diameter
        self._color = bundle.part.color.ui
        self._material = _gl_materials.Rubber(self._color.rgba_scalar)

        self._position.bind(self._update_position)
        self._build()

    def _build(self):
        vertices, faces = _sphere.create(float(self._diameter) / 2.0)
        tris, nrmls, count = self._get_triangles(vertices, faces)

        tris += self._position

        p1, p2 = self._compute_rect(tris)
        self._rect = [[p1, p2]]
        self._bb = [self._compute_bb(p1, p2)]

        self._triangles = [_base3d.TriangleRenderer([[tris, nrmls, count]], self._material)]

    def _get_triangles(self, vertices, faces):
        if Config.modeling.smooth_bundles:
            return self._compute_smoothed_vertex_normals(vertices, faces)
        else:
            return self._compute_vertex_normals(vertices, faces)

    def set_diameter(self, parent_bundle, value: _decimal):
        self._diameter = value

        self._build()

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
