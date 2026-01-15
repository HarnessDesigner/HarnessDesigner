from typing import TYPE_CHECKING

from geometry import point as _point
import compute_normals as _compute_normals

import model_to_mesh

if TYPE_CHECKING:
    from canvas import canvas as _canvas


class Config:

    class modeling:
        smooth_wires = True
        smooth_housings = False
        smooth_bundles = True
        smooth_transitions = True
        smooth_terminals = True
        smooth_cpa_locks = False
        smooth_tpa_locks = False
        smooth_boots = True
        smooth_covers = False
        smooth_splices = False
        smooth_markers = True
        smooth_seals = False
        smooth_mesh = True

        smooth_weight = 'uniform'  # 'angle', 'area', or 'uniform'


class GLObject:
    """
    Base class for objects that are to be rendered

    This class needs to be subclassed
    """

    def __init__(self):
        self.canvas: "_canvas.Canvas" = None
        # models is a list of build123d objects
        self.models = []

        # (normals, triangles, triangle_count)
        self._triangles = []

        self._is_selected = False
        self._center: _point.Point = None

        # This should be populated with 2 Point instances
        self.hit_test_rect = []

    @property
    def triangles(self):
        return self._triangles

    def get_parent_object(self) -> "GLObject":
        return self

    def adjust_hit_points(self):
        for i, (p1, p2) in enumerate(self.hit_test_rect):

            xmin = min(p1.x, p2.x)
            ymin = min(p1.y, p2.y)
            zmin = min(p1.z, p2.z)
            xmax = max(p1.x, p2.x)
            ymax = max(p1.y, p2.y)
            zmax = max(p1.z, p2.z)

            p1 = _point.Point(xmin, ymin, zmin)
            p2 = _point.Point(xmax, ymax, zmax)

            self.hit_test_rect[i] = [p1, p2]

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    @is_selected.setter
    def is_selected(self, value: bool):
        self._is_selected = value

    @staticmethod
    def get_housing_triangles(model):
        if Config.modeling.smooth_housings:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_bundle_triangles(model):
        if Config.modeling.smooth_bundles:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_transition_triangles(model):
        if Config.modeling.smooth_transitions:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_terminal_triangles(model):
        if Config.modeling.smooth_terminals:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_cpa_lock_triangles(model):
        if Config.modeling.smooth_cpa_locks:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_tpa_lock_triangles(model):
        if Config.modeling.smooth_tpa_locks:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_boot_triangles(model):
        if Config.modeling.smooth_boots:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_cover_triangles(model):
        if Config.modeling.smooth_covers:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_splice_triangles(model):
        if Config.modeling.smooth_splices:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_wire_marker_triangles(model):
        if Config.modeling.smooth_markers:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_seal_triangles(model):
        if Config.modeling.smooth_seals:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_wire_triangles(model):
        if Config.modeling.smooth_wires:
            return model_to_mesh.get_smooth_triangles(model)
        else:
            return model_to_mesh.get_triangles(model)

    @staticmethod
    def get_mesh_triangles(vertices, faces):
        if Config.modeling.smooth_mesh:
            tris, normals = _compute_normals.compute_smoothed_vertex_normals(vertices, faces)
        else:
            tris, normals = _compute_normals.compute_vertex_normals(vertices, faces)

        return tris, normals, len(tris) * 3

    def hit_test(self, point: _point.Point) -> bool:
        p1, p2 = self.hit_test_rect[0]

        return p1 <= point <= p2

    def release_mouse(self):
        raise NotImplementedError

