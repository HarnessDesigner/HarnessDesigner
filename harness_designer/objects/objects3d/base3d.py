# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from ... import color as _color
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry.decimal import Decimal as _d
from ... import config as _config
from ...gl import materials as _materials
from ... import utils as _utils
from ...gl import vbo as _vbo

from ... import debug as _debug


if TYPE_CHECKING:
    from ...database import project_db as _project_db
    from ...database.global_db import model3d as _model3d
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui


Config = _config.Config.editor3d
_debug_config = _config.Config.debug.rendering3d


class Base3D:
    """Represent a base 3D in :mod:`harness_designer.objects.objects3d.base3d`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    db_obj: "_project_db.PJTEntryBase"

    # Floor lock keeps a freely-placed object (a Housing dragged into the
    # scene) from clipping below the ground plane. Subclasses whose
    # position is always derived from a parent object (Terminal from its
    # cavity, etc.) rather than placed directly by the user should set this
    # True -- otherwise the one-time snap in __init__ silently overwrites a
    # correctly-computed position (and persists the overwrite to the DB).
    _floor_lock_exempt: bool = False

    # Object-picking priority (see gl.canvas3d.object_picker.find_object).
    # Wins outright over lower-priority objects hit by the same click ray,
    # regardless of which is nearer -- needed for handle-type objects
    # (WireMarker, WireLayout, BundleLayout) that legitimately sit inside
    # their parent wire/bundle's own OBB, sometimes with zero radial
    # offset, where the parent's tube surface is genuinely the nearer
    # ray hit and pure nearest-hit picking could never select the handle.
    _pick_priority: int = 0

    # Local-canvas mouse position that opened this object's context menu,
    # stashed by mainframe.py's _on_obj_right_click_3d right before it
    # calls get_context_menu() -- a plain instance attribute rather than a
    # get_context_menu() parameter so every other Base3D subclass's
    # get_context_menu(self) override keeps working unchanged. Only
    # Wire.get_context_menu/WireMenu currently reads this (to place a new
    # marker at the actual click point instead of the wire's midpoint).
    _context_menu_click_pos: "_point.Point | None" = None

    def __init__(self, parent: "_ObjectBase", db_obj: "_project_db.PJTEntryBase",
                 vbo: _vbo.PooledVBOHandler, angle: _angle.Angle,
                 position: _point.Point, scale: _point.Point,
                 material: _materials.GLMaterial):

        self.parent: "_ObjectBase" = parent
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

        if self._vbo is not None:
            self._vbo.acquire()

        self._is_selected = False
        self.numpy_position = self._position.as_numpy

        try:
            self._is_visible = db_obj.is_visible3d  # NOQA
            self.db_obj.bind(self._is_visible_callback, 'is_visible3d')
        except AttributeError:
            self._is_visible = False

        self._is_opaque = np.array([int(material.is_opaque)], dtype=np.uint8)
        self._aabb: np.ndarray = np.ascontiguousarray(np.array(
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float32))

        self._obb: np.ndarray = None

        self._compute_obb()
        self._compute_aabb()

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            y = _d(position.y)
            y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

            position.y = float(y)

        position.bind(self._update_position)
        angle.bind(self._update_angle)
        scale.bind(self._update_scale)

    def _is_visible_callback(self, *_, **__):
        self._is_visible = self.db_obj.is_visible3d  # NOQA
        self.mainframe.editor3d.Refresh()


    @_debug.logfunc
    def _set_model(self, model: "_model3d.Model3D"):
        self.parent.mainframe.editor3d.context.acquire()

        uuid = model.uuid

        try:
            # this checks the stored part size against the actual calculated
            # size of the part using the models obb. This is done with the angle
            # of the part set beforehand.
            o_size = self.db_obj.part.size  # NOQA
            size = model.size
            if size != o_size:
                self.db_obj.part.size = size  # NOQA
        except AttributeError:
            pass

        if uuid in _vbo.PooledVBOHandler:
            vbo = _vbo.PooledVBOHandler(uuid)
        else:
            packed = np.load(model.data_path).reshape(-1, 3)

            angle = model.angle3d
            position = model.position3d
            count = model.vertex_count

            obb = model.obb
            aabb = model.aabb

            obb @= angle
            aabb @= angle

            obb += position
            aabb += position

            packed @= angle
            packed[:count] += position

            packed = packed.reshape(-1)

            vbo = _vbo.PooledVBOHandler(uuid, packed, count, aabb=aabb, obb=obb)
        vbo.acquire()

        self._vbo = vbo
        try:
            scale = self.db_obj.scale3d  # NOQA
            self._scale.unbind(self._update_scale)
            self._scale = scale
            self._o_scale = self._scale.copy()
            self._scale.bind(self._update_scale)

        except AttributeError:
            pass

        self.position.unbind(self._update_position)
        self.angle.unbind(self._update_angle)

        self._compute_obb()
        self._compute_aabb()

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            y = _d(self.position.y)
            y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

            self.position.y = float(y)

        self.position.bind(self._update_position)
        self.angle.bind(self._update_angle)

        self.parent.mainframe.editor3d.context.release()

        self.editor3d.Refresh()

    def _compute_obb(self):
        if self._vbo is None:
            return
        local_obb = self._vbo.local_obb * self._scale
        local_obb @= self._angle
        self._obb = local_obb + self._position

    def _compute_aabb(self):
        if self._vbo is None:
            return
        local_min = self._vbo.local_aabb[0]
        local_max = self._vbo.local_aabb[1]

        x1, y1, z1 = local_min
        x2, y2, z2 = local_max

        corners = np.array([
            [x1, y1, z1], [x1, y1, z2],
            [x1, y2, z1], [x1, y2, z2],
            [x2, y1, z1], [x2, y1, z2],
            [x2, y2, z1], [x2, y2, z2]
        ], dtype=np.float32)

        corners *= self._scale.as_numpy
        corners @= self._angle
        corners += self._position.as_numpy

        aabb = _utils.adjust_aabb(corners)

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = aabb[i][j]

    def identify(self, material: list[float] | None):
        """Execute the identify operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param material: Value for ``color``.
        :type material: list[float] | None
        """
        pass

    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """
        self.editor3d.context.acquire()

        self._compute_obb()
        self._compute_aabb()

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            y = _d(position.y)
            y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

            position.unbind(self._update_position)
            position.y = float(y)
            position.bind(self._update_position)

        self._o_position = position.copy()
        self.numpy_position[:] = position.as_numpy

        self._compute_obb()
        self._compute_aabb()

        self.editor3d.context.release()
        self.editor3d.Refresh(False)

    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        self.editor3d.context.acquire()

        self._o_angle = angle.copy()
        self._angle_inverse = -angle

        self._compute_obb()
        self._compute_aabb()

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            y = _d(self._position.y)
            y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

            self._position.unbind(self._update_position)
            self._position.y = float(y)
            self._position.bind(self._update_position)

            self.editor3d.context.release()

            return

        self.editor3d.context.release()

        self.editor3d.Refresh(False)

    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """
        self.editor3d.context.acquire()

        self._o_scale = scale.copy()

        self._compute_obb()
        self._compute_aabb()

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            y = _d(self._position.y)
            y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

            self._position.unbind(self._update_position)
            self._position.y = float(y)
            self._position.bind(self._update_position)

            self.editor3d.context.release()
            return

        self.editor3d.context.release()

        self.editor3d.Refresh(False)

    @property
    def position(self) -> _point.Point:
        """Return the position.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self._position

    @position.setter
    def position(self, value: _point.Point):
        """Set the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value for ``_``.
        :type value: :class:`_point.Point`
        :raises AttributeError: Raised when the operation cannot be completed.
        """
        if id(value) != id(self._position):
            raise AttributeError('Position is only able to be modified not set')

        self._position = value

    @property
    def angle(self) -> _angle.Angle:
        """
        Return the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_angle.Angle`
        """

        return self._angle

    @angle.setter
    def angle(self, value: _angle.Angle):
        """
        Set the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value for ``_``.
        :type value: :class:`_angle.Angle`
        :raises AttributeError: Raised when the operation cannot be completed.
        """

        if id(value) != id(self._angle):
            raise AttributeError('Angle is only able to be modified not set')

        self._angle = value

    @property
    def scale(self) -> _point.Point:
        """Return the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_point.Point`
        """
        return self._scale

    @scale.setter
    def scale(self, value: _point.Point):
        """Set the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value for ``_``.
        :type value: :class:`_point.Point`
        :raises AttributeError: Raised when the operation cannot be completed.
        """

        if id(value) != id(self._scale):
            raise AttributeError('Scale is only able to be modified not set')

        self._scale = value

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
        if self._vbo is None:
            return False

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
        if self._vbo is None:
            return False

        ray_object = ray_origin - self._position

        vertices = (self._vbo.vertices.reshape(-1, 3) * self._scale) @ self._angle

        if len(vertices) % 3:
            return False

        verts = vertices.reshape(-1, 3, 3)

        # Vectorized ray-triangle intersection
        hit = self._ray_triangles_intersect_vectorized(ray_object, ray_dir, verts)

        return hit

    @staticmethod
    def _ray_triangles_intersect_vectorized(
        ray_origin, ray_dir, vertices, max_t=None):  # NOQA

        """
        Vectorized Möller-Trumbore ray-triangle intersection

        Tests ray against MANY triangles at once using NumPy broadcasting

        Args:
            ray_origin: (3,) array
            ray_dir: (3,) array
            vertices: (N, 3, 3) array - N triangles, each with 3 vertices of 3 coords
            max_t: optional upper bound on the hit distance -- pass the
                edge's own length (with ray_dir as the unnormalized edge
                vector, i.e. t=1 reaches the far endpoint) to test a finite
                segment instead of an infinite ray. None (default) preserves
                the original unbounded-ray behavior used for picking.

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
        if max_t is not None:
            hit_mask = hit_mask & (t <= max_t)

        return np.any(hit_mask)

    @property
    def obb(self) -> np.ndarray:
        """Return the OBB.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`np.ndarray`
        """
        return self._obb

    @property
    def aabb(self) -> np.ndarray:
        """Return the AABB.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`np.ndarray`
        """
        return self._aabb

    @property
    def is_selected(self) -> bool:
        """Return the is selected.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_selected

    def set_selected(self, flag: bool):
        """Set the selected.

        UNKNOWN details are inferred from the callable name and signature.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        if flag:
            self._material = self._selected_material
        else:
            self._material = self._unselected_material

        self._is_opaque[0] = int(self._material.is_opaque)
        self._is_selected = flag

    def delete(self):
        """Execute the delete operation.

        UNKNOWN details are inferred from the callable name and signature.
        """
        self.db_obj.delete()

    @property
    def material(self):
        """Return the material.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        if self._is_selected:
            return self._selected_material

        return self._material

    def _render_geometry(self, program, pos_loc, rot_loc, scale_loc, normal_loc=None):
        """Render the object geometry using the active shader program.

        Called by render() for each rendering pass (faces, edges, normals, vertices).
        Sets the per-object transform uniforms (position, rotation, scale) and
        issues the draw call via vertex attribute arrays or the VBO.
        """

        smooth = int(getattr(self, 'smooth', False))

        if self._vbo is None:
            return
        if normal_loc is not None:
            GL.glUniform1i(normal_loc, int(getattr(self, 'smooth', False)))
        GL.glUniform3f(pos_loc, *self._position.as_float)
        GL.glUniform4f(rot_loc, *[float(str(v)) for v in self._angle.as_quat_numpy.tolist()])
        GL.glUniform3f(scale_loc, *self._scale.as_float)

        self._vbo.render()

    def render(self, faces_program, edges_program, vertices_program):
        """Execute the render operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param faces_program: Value for ``faces_program``.
        :type faces_program: UNKNOWN
        :param edges_program: Value for ``edges_program``.
        :type edges_program: UNKNOWN
        :param vertices_program: Value for ``vertices_program``.
        :type vertices_program: UNKNOWN
        """
        if not self.is_visible:
            return

        if self._vbo is not None and self._vbo.is_dirty:
            self._compute_aabb()
            self._compute_obb()

        if _debug_config.draw_faces:
            GL.glUseProgram(faces_program)

            self.material.set(faces_program)

            # Set object transformation uniforms
            pos_loc = GL.glGetUniformLocation(faces_program, "objectPosition")
            rot_loc = GL.glGetUniformLocation(faces_program, "objectRotation")
            scale_loc = GL.glGetUniformLocation(faces_program, "objectScale")
            normal_loc = GL.glGetUniformLocation(faces_program, "normalMode")

            self._render_geometry(faces_program, pos_loc, rot_loc, scale_loc, normal_loc)

        if _debug_config.draw_edges:
            material_color = self.material.diffuse[:3]  # Get RGB

            # Calculate perceived brightness using standard luminance formula
            # Human eye perceives green more than red, and red more than blue
            luminance = (0.299 * material_color[0] +
                         0.587 * material_color[1] +
                         0.114 * material_color[2])

            if luminance < _debug_config.edge_luminance_threshold:
                e_color = _debug_config.edge_color_dark[:] + [1.0]
            else:
                e_color = _debug_config.edge_color_light[:] + [1.0]

            GL.glUseProgram(edges_program)

            material = _materials.Metallic(_color.Color(*e_color))

            material.set(edges_program)

            pos_loc = GL.glGetUniformLocation(edges_program, "objectPosition")
            rot_loc = GL.glGetUniformLocation(edges_program, "objectRotation")
            scale_loc = GL.glGetUniformLocation(edges_program, "objectScale")
            render_loc = GL.glGetUniformLocation(edges_program, "renderMode")
            normal_loc = GL.glGetUniformLocation(edges_program, "normalMode")

            GL.glUniform1i(render_loc, 0)

            self._render_geometry(edges_program, pos_loc, rot_loc, scale_loc, normal_loc)

        if _debug_config.draw_normals:
            p1, p2 = self.aabb
            width = abs(p2[0] - p1[0])
            height = abs(p2[1] - p1[1])
            depth = abs(p2[2] - p1[2])
            smallest_dimension = min(width, height, depth)
            dynamic_normal_length = smallest_dimension / 10.0

            GL.glUseProgram(edges_program)

            color = _debug_config.normals_color[:] + [1.0]
            material = _materials.Glowing(_color.Color(*color))
            material.set(edges_program)

            pos_loc = GL.glGetUniformLocation(edges_program, "objectPosition")
            rot_loc = GL.glGetUniformLocation(edges_program, "objectRotation")
            scale_loc = GL.glGetUniformLocation(edges_program, "objectScale")
            render_loc = GL.glGetUniformLocation(edges_program, "renderMode")
            normal_length_loc = GL.glGetUniformLocation(edges_program, "normalLength")
            normal_loc = GL.glGetUniformLocation(edges_program, "normalMode")

            GL.glUniform1i(render_loc, 1)
            GL.glUniform1f(normal_length_loc, dynamic_normal_length)

            self._render_geometry(edges_program, pos_loc, rot_loc, scale_loc, normal_loc)

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
        """Render the AABB.

        UNKNOWN details are inferred from the callable name and signature.
        """
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
            """Render the edges.

            UNKNOWN details are inferred from the callable name and signature.

            :param v: Value for ``v``.
            :type v: UNKNOWN
            :param e: Value for ``e``.
            :type e: UNKNOWN
            """
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
        """Render the OBB.

        UNKNOWN details are inferred from the callable name and signature.
        """
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
            """Render the bb.

            UNKNOWN details are inferred from the callable name and signature.

            :param v: Value for ``v``.
            :type v: UNKNOWN
            :param f: Value for ``f``.
            :type f: UNKNOWN
            """
            vers, normals, count = _utils.compute_face_normals(v, f)

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
            """Render the edges.

            UNKNOWN details are inferred from the callable name and signature.

            :param v: Value for ``v``.
            :type v: UNKNOWN
            :param e: Value for ``e``.
            :type e: UNKNOWN
            """
            e = v[e].reshape(-1, 3)
            GL.glLineWidth(1.0)
            GL.glEnableClientState(GL.GL_VERTEX_ARRAY)

            GL.glVertexPointer(3, GL.GL_FLOAT, 0, e)
            GL.glDrawArrays(GL.GL_LINES, 0, len(e))

            GL.glDisableClientState(GL.GL_VERTEX_ARRAY)

        GL.glColor4f(0.5, 1.0, 0.5, 0.3)
        _render_bb(vertices.reshape(-1, 3), faces)

        GL.glColor4f(0.5, 1.0, 0.5, 1.0)
        _render_edges(vertices.reshape(-1, 3), edges)

    @property
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_visible

    @is_visible.setter
    def is_visible(self, value: bool):
        """Set the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bool
        """
        self._is_visible = value
        try:
            self.db_obj.is_visible3d = value
        except AttributeError:
            pass

    @property
    def is_opaque(self):
        """Return the is opaque.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._is_opaque

    def get_context_menu(self):
        """Return the context menu.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return None
