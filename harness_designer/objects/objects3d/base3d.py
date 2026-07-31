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
from .. import objectsvar as _objectsvar

from ... import debug as _debug
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ...database import project_db as _project_db
    from ...database.global_db import model3d as _model3d
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui


Config = _config.Config.editor3d
_debug_config = _config.Config.debug.rendering3d


class Base3D(_objectsvar.BaseVar):
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

    # Object-picking priority (see gl.object_picker.find_object).
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
    _context_menu_click_pos: _point.Point | None = None

    @_check_types.do
    def __init__(self, parent: "_ObjectBase", db_obj: "_project_db.PJTEntryBase",
                 vbo: _vbo.PooledVBOHandler, angle: _angle.Angle,
                 position: _point.Point, scale: _point.Point,
                 material: _materials.GLMaterial):

        self.editor3d = parent.mainframe.editor3d

        super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        self.parent: "_ObjectBase" = parent
        self.mainframe: "_ui.MainFrame" = parent.mainframe

        try:
            self._is_visible = db_obj.is_visible3d  # NOQA
            self.db_obj.bind(self._is_visible_callback, 'is_visible3d')
        except AttributeError:
            self._is_visible = False

        position.unbind(self._update_position)
        angle.unbind(self._update_angle)
        scale.unbind(self._update_scale)

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

    @property
    @_check_types.do
    def _selected_color(self) -> _color.Color:
        return _color.Color(*Config.selected_color)

    @property
    @_check_types.do
    def editor(self):
        return self.editor3d

    @_check_types.do
    def _is_visible_callback(self, *_, **__):
        self._is_visible = self.db_obj.is_visible3d  # NOQA
        self.mainframe.editor3d.Refresh()

    @_debug.logfunc
    @_check_types.do
    def _set_model(self, model: "_model3d.Model3D"):
        with self.parent.mainframe.editor3d.context:
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

        self.editor3d.Refresh()

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """Update the position.

        UNKNOWN details are inferred from the callable name and signature.

        :param position: Position value.
        :type position: :class:`_point.Point`
        """

        super()._update_position(position)

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            with self.editor3d.context:
                y = _d(position.y)
                y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

                position.unbind(self._update_position)
                position.y = float(y)
                position.bind(self._update_position)

                self._o_position = position.copy()
                self.numpy_position[:] = position.as_numpy

                self._compute_obb()
                self._compute_aabb()

            self.editor3d.Refresh(False)

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """Update the angle.

        UNKNOWN details are inferred from the callable name and signature.

        :param angle: Value for ``angle``.
        :type angle: :class:`_angle.Angle`
        """
        super()._update_angle(angle)

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            with self.editor3d.context:
                y = _d(self._position.y)
                y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

                self._position.unbind(self._update_position)
                self._position.y = float(y)
                self._position.bind(self._update_position)

    @_check_types.do
    def _update_scale(self, scale: _point.Point):
        """Update the scale.

        UNKNOWN details are inferred from the callable name and signature.

        :param scale: Value for ``scale``.
        :type scale: :class:`_point.Point`
        """

        super()._update_scale(scale)

        if (
            not self._floor_lock_exempt and
            self.editor3d.config.floor.enable_floor_lock and
            self._aabb[0][1] < Config.floor.ground_height
        ):
            with self.editor3d.context:
                y = _d(self._position.y)
                y += _d(Config.floor.ground_height) - _d(float(self._aabb[0][1]))

                self._position.unbind(self._update_position)
                self._position.y = float(y)
                self._position.bind(self._update_position)

    @_check_types.do
    def delete(self):
        """Execute the delete operation.

        Row deletion and canvas de-registration are handled once, centrally,
        by :meth:`ObjectBase.delete`. Subclasses override this as their hook
        for view-local teardown (see :meth:`objects3d.housing.Housing.delete`).
        """
        self.parent.delete()

    @_check_types.do
    def _delete(self):
        """
        Any object specific taredown should occur in this function
        """
        self._is_deleted = True
        self.editor3d.Refresh()

    @_check_types.do
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

    @_check_types.do
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

    @_check_types.do
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

        @_check_types.do
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

    @_check_types.do
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

        @_check_types.do
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

        @_check_types.do
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
    @_check_types.do
    def is_visible(self) -> bool:
        """Return the is visible.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return self._is_visible

    @is_visible.setter
    @_check_types.do
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
