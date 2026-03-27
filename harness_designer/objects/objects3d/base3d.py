from typing import TYPE_CHECKING, Union

import numpy as np
from OpenGL import GL

from ... import debug as _debug
from ... import color as _color
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry import line as _line

from ...geometry.decimal import Decimal as _d
from ... import config as _config
from ...gl import materials as _materials
from ... import utils as _utils
from ...gl import vbo as _vbo

if TYPE_CHECKING:
    from ...database import project_db as _project_db
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui


Config = _config.Config.editor3d
_debug_config = _config.Config.debug.rendering3d


class Base3D:
    db_obj: "_project_db.PJTEntryBase"

    def __init__(self,  parent: "_ObjectBase", db_obj: "_project_db.PJTEntryBase",
                 vbo: _vbo.VBOHandler, angle: _angle.Angle,
                 position: _point.Point, scale: _point.Point,
                 material: _materials.GLMaterial, data=None):

        self._parent: "_ObjectBase" = parent
        self.editor3d = parent.mainframe.editor3d
        self.mainframe: "_ui.MainFrame" = parent.mainframe

        self.db_obj = db_obj
        self._position = position
        self._o_position = position.copy()

        self._unselected_material = material
        self._material = material

        selected_color = _color.Color(*Config.selected_color)
        self._selected_material = _materials.Generic(selected_color)

        self._angle = angle
        self._o_angle = angle.copy()

        self._angle_inverse = -self._angle

        self._scale = scale
        self._o_scale = scale.copy()

        self._vbo = vbo

        self._is_selected = False
        self.numpy_position = self._position.as_numpy

        try:
            self._is_visible = db_obj.is_visible3d  # NOQA
        except AttributeError:
            self._is_visible = False

        self._is_opaque = np.array([1], dtype=np.uint8)
        self._aabb: np.ndarray = np.ascontiguousarray(np.array(
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float64))

        self._obb: np.ndarray = None

        self._data = data

        self._compute_obb()
        self._compute_aabb()

        position.bind(self._update_position)
        angle.bind(self._update_angle)
        scale.bind(self._update_scale)

    def _compute_obb(self):
        if self._vbo is None:
            p1, p2 = _utils.compute_aabb(self._data[0])

            self._obb = _utils.compute_obb(p1, p2)
        else:
            local_obb = self._vbo.local_obb * self._scale
            local_obb @= self._angle
            self._obb = local_obb + self._position

    def _compute_aabb(self):
        if self._vbo is None:
            p1, p2 = _utils.compute_aabb(self._data[0])
            aabb = _utils.adjust_aabb(np.array([p1.as_float, p2.as_float], dtype=np.float64))
        else:
            local_min = self._vbo.local_aabb[0]
            local_max = self._vbo.local_aabb[1]

            x1, y1, z1 = local_min
            x2, y2, z2 = local_max

            corners = np.array([
                [x1, y1, z1], [x1, y1, z2],
                [x1, y2, z1], [x1, y2, z2],
                [x2, y1, z1], [x2, y1, z2],
                [x2, y2, z1], [x2, y2, z2]
            ], dtype=np.float64)

            corners *= self._scale.as_numpy
            corners @= self._angle
            corners += self._position.as_numpy

            aabb = _utils.adjust_aabb(corners)

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = aabb[i][j]

    def _update_position(self, position: _point.Point):
        self._compute_obb()
        self._compute_aabb()

        if self._vbo is not None and self._aabb[0][1] < Config.floor.ground_height:
            self._position.y += Config.floor.ground_height - self._aabb[0][1]
            return

        if self._vbo is None:
            delta = position - self._o_position
            self._data[0] += delta

        self._o_position = position.copy()
        self.numpy_position = position.as_numpy

        self._compute_obb()
        self._compute_aabb()

        self.editor3d.Refresh(False)

    def _update_angle(self, angle: _angle.Angle):
        if self._vbo is None:
            delta = angle - self._o_angle
            tris, nrmls = self._data[:-1]

            tris -= self._position
            tris @= delta
            nrmls @= delta

            tris += self._position
            self._data[0] = tris
            self._data[1] = nrmls

        self._o_angle = angle.copy()
        self._angle_inverse = -angle

        self._compute_obb()
        self._compute_aabb()

        if self._vbo is not None and self._aabb[0][1] < Config.floor.ground_height:
            self._position.y += Config.floor.ground_height - self._aabb[0][1]
            return

        self.editor3d.Refresh(False)

    def _update_scale(self, scale: _point.Point):
        self._o_scale = scale.copy()

        self._compute_obb()
        self._compute_aabb()

        if self._vbo is not None and self._aabb[0][1] < Config.floor.ground_height:
            self._position.y += Config.floor.ground_height - self._aabb[0][1]
            return

        self.editor3d.Refresh(False)

    @property
    def position(self) -> _point.Point:
        return self._position

    @position.setter
    def position(self, _):
        raise AttributeError('Position is only able to be modified not set')

    @property
    def angle(self) -> _angle.Angle:
        return self._angle

    @angle.setter
    def angle(self, _):
        raise AttributeError('Angle is only able to be modified not set')

    @property
    def scale(self) -> _point.Point:
        return self._angle

    @scale.setter
    def scale(self, _):
        raise AttributeError('Scale is only able to be modified not set')

    def hit_test_step1(self, ray_origin, ray_direction):
        """
        Stage 1: Test against cached AABB

        Super fast - just uses pre-calculated bbox_min/max
        """
        inv_dir = 1.0 / (ray_direction + 1e-8)
        t = (self._aabb - ray_origin) * inv_dir
        tmin = np.minimum(t)
        tmax = np.maximum(t)

        return np.min(tmax) >= max(0, np.max(tmin))

    def hit_test_step2(self, ray_origin, ray_direction):
        """
        Stage 2: Test against cached OBB

        Fast - uses pre-calculated rotation_inverse
        """
        local_origin = (ray_origin - self._position) @ self._angle_inverse
        local_direction = ray_direction @ self._angle_inverse

        inv_dir = 1.0 / (local_direction + 1e-8)
        t = (self._vbo.local_aabb - local_origin) * inv_dir

        tmin = np.minimum(t)
        tmax = np.maximum(t)

        return np.min(tmax) >= max(0, np.max(tmin))

    def hit_test_step3(self, ray_origin, ray_dir):
        """
        Stage 3: Vectorized ray-mesh intersection

        Uses NumPy broadcasting to test ray against ALL triangles at once
        Much faster than looping through triangles one by one
        """
        # Transform ray to object space (subtract position, no rotation yet)
        ray_object = ray_origin - self._position

        # Scale vertices to match object instance
        verts = ((self._vbo.vertices * self._scale) @ self._angle)[self._vbo.faces]

        # Vectorized ray-triangle intersection
        hit = self._ray_triangles_intersect_vectorized(ray_object, ray_dir, verts)

        return hit

    @staticmethod
    def _ray_triangles_intersect_vectorized(
        ray_origin, ray_dir, vertices):  # NOQA

        """
        Vectorized Möller-Trumbore ray-triangle intersection

        Tests ray against MANY triangles at once using NumPy broadcasting

        Args:
            ray_origin: (3,) array
            ray_dir: (3,) array
            vertices: (N, 3, 3) array - N triangles, each with 3 vertices of 3 coords

        Returns:
            hit_mask: (N,) boolean array - True where ray hits triangle
            distances: (N,) float array - distance to intersection (inf if no hit)
        """
        num_triangles = vertices.shape[0]  # NOQA

        # Extract vertices
        v0 = vertices[:, 0, :]  # (N, 3)
        v1 = vertices[:, 1, :]  # (N, 3)
        v2 = vertices[:, 2, :]  # (N, 3)

        # Edge vectors
        edge1 = v1 - v0  # (N, 3)  # NOQA
        edge2 = v2 - v0  # (N, 3)

        # Begin calculating determinant
        h = np.cross(ray_dir, edge2)  # (N, 3)  # NOQA
        det = np.sum(edge1 * h, axis=1)     # (N,) - dot product

        # Initialize output arrays
        hit_mask = np.zeros(num_triangles, dtype=bool)

        # Check determinant (ray parallel to triangle)
        valid_det = np.abs(det) > 1e-6  # (N,)

        if not np.any(valid_det):
            return np.any(hit_mask)

        inv_det = np.zeros_like(det)
        inv_det[valid_det] = 1.0 / det[valid_det]

        # Calculate distance from v0 to ray origin
        s = ray_origin - v0  # (N, 3)

        # Calculate u parameter
        u = inv_det * np.sum(s * h, axis=1)  # (N,)

        # Test u bounds
        valid_u = valid_det & (u >= 0.0) & (u <= 1.0)

        if not np.any(valid_u):
            return np.any(hit_mask)

        # Calculate v parameter
        q = np.cross(s, edge1)  # (N, 3)  # NOQA
        v = inv_det * np.sum(ray_dir * q, axis=1)  # (N,)

        # Test v bounds
        valid_v = valid_u & (v >= 0.0) & (u + v <= 1.0)

        if not np.any(valid_v):
            return np.any(hit_mask)

        # Calculate t (distance along ray)
        t = inv_det * np.sum(edge2 * q, axis=1)  # (N,)

        # Final validation: t > epsilon (ray, not line)
        hit_mask = valid_v & (t > 1e-6)

        return np.any(hit_mask)

    @property
    def obb(self) -> np.ndarray:
        return self._obb

    @property
    def aabb(self) -> np.ndarray:
        return self._aabb

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    def set_selected(self, flag: bool):
        if flag:
            self._material = self._selected_material
        else:
            self._material = self._unselected_material

        self._is_opaque[0] = int(self._material.is_opaque)
        self._is_selected = flag

        if flag:
            self.mainframe._set_selected(self._parent)  # NOQA
        else:
            self.mainframe._set_selected(None)  # NOQA

    def delete(self):
        self.db_obj.delete()

    @property
    def material(self):
        if self._is_selected:
            return self._selected_material

        return self._material

    def _render_geometry(self, active_shader, pos_loc, rot_loc, scale_loc):
        """Render the object geometry using the active shader program.

        Called by render() for each rendering pass (faces, edges, normals, vertices).
        Sets the per-object transform uniforms (position, rotation, scale) and
        issues the draw call via vertex attribute arrays or the VBO.
        """
        if self._vbo is None:
            GL.glUniform3f(pos_loc, 0.0, 0.0, 0.0)
            GL.glUniform4f(rot_loc, 1.0, 0.0, 0.0, 0.0)
            GL.glUniform3f(scale_loc, 1.0, 1.0, 1.0)

            verts, nrmls, count = self._data

            GL.glEnableVertexAttribArray(0)
            GL.glEnableVertexAttribArray(1)

            GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, verts)
            GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, nrmls)

            GL.glDrawArrays(GL.GL_TRIANGLES, 0, count)

            GL.glDisableVertexAttribArray(0)
            GL.glDisableVertexAttribArray(1)
        else:
            GL.glUniform3f(pos_loc, *self._position.as_float)
            GL.glUniform4f(rot_loc, *self._angle.as_quat_numpy.tolist())
            GL.glUniform3f(scale_loc, *self._scale.as_float)

            self._vbo.render()

    def render(self, faces_program, edges_program, vertices_program):
        if not self.is_visible:
            return

        if _debug_config.draw_faces:
            GL.glUseProgram(faces_program)

            self.material.set(faces_program)

            # Set object transformation uniforms
            pos_loc = GL.glGetUniformLocation(faces_program, "objectPosition")
            rot_loc = GL.glGetUniformLocation(faces_program, "objectRotation")
            scale_loc = GL.glGetUniformLocation(faces_program, "objectScale")

            self._render_geometry(faces_program, pos_loc, rot_loc, scale_loc)

        if _debug_config.draw_edges:
            material_color = self.material.diffuse[:3]  # Get RGB

            # Calculate perceived brightness using standard luminance formula
            # Human eye perceives green more than red, and red more than blue
            luminance = (0.299 * material_color[0] +
                         0.587 * material_color[1] +
                         0.114 * material_color[2])

            if luminance < _debug_config.edge_luminance_threshold:
                e_color = _debug_config.edge_color_dark
            else:
                e_color = _debug_config.edge_color_light

            GL.glUseProgram(edges_program)

            pos_loc = GL.glGetUniformLocation(edges_program, "objectPosition")
            rot_loc = GL.glGetUniformLocation(edges_program, "objectRotation")
            scale_loc = GL.glGetUniformLocation(edges_program, "objectScale")
            render_mode_loc = GL.glGetUniformLocation(edges_program, "renderMode")
            edge_color_loc = GL.glGetUniformLocation(edges_program, "edgeColor")

            GL.glUniform1i(render_mode_loc, 0)
            GL.glUniform3f(edge_color_loc, *e_color)

            self._render_geometry(edges_program, pos_loc, rot_loc, scale_loc)

        if _debug_config.draw_normals:
            p1, p2 = self.aabb
            width = abs(p2[0] - p1[0])
            height = abs(p2[1] - p1[1])
            depth = abs(p2[2] - p1[2])
            smallest_dimension = min(width, height, depth)
            dynamic_normal_length = smallest_dimension / 10.0

            GL.glUseProgram(edges_program)

            pos_loc = GL.glGetUniformLocation(edges_program, "objectPosition")
            rot_loc = GL.glGetUniformLocation(edges_program, "objectRotation")
            scale_loc = GL.glGetUniformLocation(edges_program, "objectScale")
            render_mode_loc = GL.glGetUniformLocation(edges_program, "renderMode")
            normal_length_loc = GL.glGetUniformLocation(edges_program, "normalLength")

            GL.glUniform1i(render_mode_loc, 1)
            GL.glUniform1f(normal_length_loc, dynamic_normal_length)

            self._render_geometry(edges_program, pos_loc, rot_loc, scale_loc)

        if _debug_config.draw_vertices:
            GL.glUseProgram(vertices_program)

            pos_loc = GL.glGetUniformLocation(vertices_program, "objectPosition")
            rot_loc = GL.glGetUniformLocation(vertices_program, "objectRotation")
            scale_loc = GL.glGetUniformLocation(vertices_program, "objectScale")
            vertex_color_loc = GL.glGetUniformLocation(vertices_program, "vertexColor")

            GL.glUniform3f(vertex_color_loc, *_debug_config.vertices_color)  # Red vertices

            self._render_geometry(vertices_program, pos_loc, rot_loc, scale_loc)

        if self.is_selected:
            GL.glUseProgram(0)

            if _debug_config.draw_obb:
                self._render_obb()

            if _debug_config.draw_aabb:
                self._render_aabb()

            GL.glColor4f(1.0, 0.4, 0.4, 1.0)
            GL.glLineWidth(2.0)
            p1, p2 = self.aabb

            y = Config.floor.ground_height + 0.20

            GL.glBegin(GL.GL_LINES)
            GL.glVertex3f(p1[0], y, p1[2])
            GL.glVertex3f(p1[0], y, p2[2])

            GL.glVertex3f(p1[0], y, p2[2])
            GL.glVertex3f(p2[0], y, p2[2])

            GL.glVertex3f(p2[0], y, p2[2])
            GL.glVertex3f(p2[0], y, p1[2])

            GL.glVertex3f(p2[0], y, p1[2])
            GL.glVertex3f(p1[0], y, p1[2])
            GL.glEnd()

    def _render_aabb(self):
        aabb = self.aabb

        x1, y1, z1 = aabb[0]
        x2, y2, z2 = aabb[1]

        vertices = np.array([
                [x1, y1, z1],  # 0: bottom-left-front
                [x2, y1, z1],  # 1: bottom-right-front
                [x2, y2, z1],  # 2: top-right-front
                [x1, y2, z1],  # 3: top-left-front
                [x1, y1, z2],  # 4: bottom-left-back
                [x2, y1, z2],  # 5: bottom-right-back
                [x2, y2, z2],  # 6: top-right-back
                [x1, y2, z2],  # 7: top-left-back
            ], dtype=np.float32)

        edges = np.array([
                (0, 1), (1, 2), (2, 3), (3, 0),  # front face
                (4, 5), (5, 6), (6, 7), (7, 4),  # back face
                (0, 4), (1, 5), (2, 6), (3, 7),  # connecting edges
            ], dtype=np.int32)

        def _render_edges(v, e):
            e = v[e].reshape(-1, 3)
            GL.glLineWidth(1.5)
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)

            GL.glVertexPointer(3, GL.GL_FLOAT, 0, e)
            GL.glDrawArrays(GL.GL_LINES, 0, len(e))

            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

        # render edges
        GL.glColor4f(1.0, 0.2, 0.2, 1.0)
        _render_edges(vertices, edges)

    def _render_obb(self):
        vertices = self.obb

        faces = np.array([
                (0, 1, 2, 3),  # front
                (5, 4, 7, 6),  # back
                (4, 0, 3, 7),  # left
                (1, 5, 6, 2),  # right
                (3, 2, 6, 7),  # top
                (4, 5, 1, 0),  # bottom
            ], dtype=np.int32)

        edges = np.array([
                (0, 1), (1, 2), (2, 3), (3, 0),  # front face
                (4, 5), (5, 6), (6, 7), (7, 4),  # back face
                (0, 4), (1, 5), (2, 6), (3, 7),  # connecting edges
            ], dtype=np.int32)

        def _render_bb(v, f):
            vers, normals, count = _utils.compute_vertex_normals(v, f)

            # Enable vertex arrays
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
            GL.glEnableClientState(GL.GL_NORMAL_ARRAY)

            # Set pointers
            GL.glVertexPointer(3, GL.GL_FLOAT, 0, vers)
            GL.glNormalPointer(GL.GL_FLOAT, 0, normals)

            # Draw all quads
            GL.glDrawArrays(GL.GL_QUADS, 0, count)

            # Disable vertex arrays
            GL.glDisableClientState(GL.GL_NORMAL_ARRAY)
            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

        def _render_edges(v, e):
            e = v[e].reshape(-1, 3)
            GL.glLineWidth(1.0)
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)

            GL.glVertexPointer(3, GL.GL_FLOAT, 0, e)
            GL.glDrawArrays(GL.GL_LINES, 0, len(e))

            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

        GL.glColor4f(0.5, 1.0, 0.5, 0.3)
        _render_bb(vertices, faces)

        GL.glColor4f(0.5, 1.0, 0.5, 1.0)
        _render_edges(vertices, edges)

    @property
    def is_visible(self) -> bool:
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool):
        self._is_visible = value
        try:
            self.db_obj.is_visible3d = value
        except AttributeError:
            pass

    @property
    def is_opaque(self):
        return self._is_opaque

    def get_context_menu(self):
        raise NotImplementedError

