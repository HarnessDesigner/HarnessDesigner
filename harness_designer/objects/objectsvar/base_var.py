# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union

import numpy as np
from OpenGL import GL

from ... import color as _color
from ...geometry import point as _point
from ...geometry import angle as _angle
from ... import config as _config
from ...gl import materials as _materials
from ... import utils as _utils
from ...gl import vbo as _vbo_base
from ...shapes import text as _text
from ... import check_types as _check_types

if TYPE_CHECKING:
    from ...database import project_db as _project_db
    from .. import ObjectBase as _ObjectBase


Config = _config.Config.colors
_debug_config = _config.Config.debug.rendering3d


class BaseVar:

    # Tie-breaker for gl.object_picker.find_object when multiple
    # OBB/AABB hits land on the same ray -- see Base3D._pick_priority
    # (WireMarker/WireLayout/BundleLayout bump this to 1 to win over the
    # wire they sit on/inside).
    _pick_priority: int = 0

    # Explicit class-level type for every subclass whose own _vbo is a
    # real mesh VBO handler (the common case) -- a subclass whose own
    # _vbo is instead a shapes.text.Text (a Note, see objects_3d/
    # objects_schematic/objects_pegboard's own note.py) redeclares this
    # narrower, to its own actual type, at the class level (not just in
    # __init__'s own parameter annotation, which every subclass shares
    # regardless of which one it actually ends up holding).
    _vbo: "_vbo_base.VBOHandlerBase | None" = None

    @_check_types.do
    def __init__(self, parent: "_ObjectBase", db_obj: Union["_project_db.PJTEntryBase", None],
                 vbo: _vbo_base.VBOHandlerBase | _text.Text | None,
                 angle: _angle.Angle | None, position: _point.Point | None,
                 scale: _point.Point | None, material: _materials.GLMaterial | None):

        self._is_selected = False
        self._is_visible = False

        self.parent = parent
        self.db_obj = db_obj
        self._vbo = vbo
        self._angle = angle
        self._position = position
        self._scale = scale
        self._material = material
        self._unselected_material = material

        self._selected_material = _materials.Generic(self._selected_color)

        if angle is None:
            self._o_angle = None
            self._angle_inverse = None
        else:
            self._o_angle = angle.copy()
            self._angle_inverse = -angle
            angle.bind(self._update_angle)

        if position is None:
            self._o_position = None
            self.numpy_position = None
        else:
            self._o_position = position.copy()
            position.bind(self._update_position)
            self.numpy_position = self._position.as_numpy

        if scale is None:
            self._o_scale = None
        else:
            self._o_scale = scale.copy()
            scale.bind(self._update_scale)

        if material is None:
            self._is_opaque = np.array([1], dtype=np.uint8)
        else:
            self._is_opaque = np.array([int(material.is_opaque)], dtype=np.uint8)

        self._aabb: np.ndarray = np.ascontiguousarray(np.array(
            [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=np.float32))

        self._obb: np.ndarray = None

        self._compute_obb()
        self._compute_aabb()

        if db_obj is not None:
            try:
                self._smooth = db_obj.smooth  # NOQA

                db_obj.bind(self.__update_smooth, 'smooth')
            except AttributeError:
                self._smooth = True
        else:
            self._smooth = True

    def __update_smooth(self, *_, **__):
        self._smooth = self.db_obj.smooth  # NOQA

    @property
    def smooth(self) -> bool:
        if self._smooth is None:
            return True

        return self._smooth

    @smooth.setter
    def smooth(self, value: bool | None):
        self._smooth = value

        try:
            self.db_obj.smooth = value
        except AttributeError:
            pass

    @property
    @_check_types.do
    def _selected_color(self) -> _color.Color:
        raise NotImplementedError

    @property
    @_check_types.do
    def selected_material(self) -> _materials.GLMaterial:
        """This object's own "selected" material -- exposed publicly so
        other objects can identify() themselves with it (e.g. a Wire
        showing its own WireLayouts in the selected color while the
        layouts themselves aren't the true selection; see
        objects.wire.Wire.set_selected)."""
        return self._selected_material

    @property
    @_check_types.do
    def vbo(self):
        return self._vbo

    @property
    @_check_types.do
    def editor(self):
        raise NotImplementedError

    @_check_types.do
    def _is_visible_callback(self, *_, **__):
        raise NotImplementedError

    @_check_types.do
    def _compute_obb(self):
        if self._vbo is None:
            return

        if self._position is None:
            return

        if self._scale is None:
            return

        if self._angle is None:
            return

        local_obb = self._vbo.local_obb * self._scale
        local_obb @= self._angle
        self._obb = local_obb + self._position

    @_check_types.do
    def _compute_aabb(self):
        if self._vbo is None:
            return

        if self._position is None:
            return

        if self._scale is None:
            return

        if self._angle is None:
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

    @_check_types.do
    def hit_test_step1(self, ray_origin, ray_direction):
        """
        Stage 1: Test against cached AABB

        Super fast - just uses pre-calculated bbox_min/max
        """
        inv_dir = 1.0 / (ray_direction + 1e-8)
        t = (self._aabb - ray_origin) * inv_dir
        tmin = np.minimum(t[0], t[1])
        tmax = np.maximum(t[0], t[1])

        return np.min(tmax) >= max(0, np.max(tmin))

    @_check_types.do
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

        tmin = np.minimum(t[0], t[1])
        tmax = np.maximum(t[0], t[1])

        return np.min(tmax) >= max(0, np.max(tmin))

    @_check_types.do
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
    @_check_types.do
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

    @_check_types.do
    def identify(self, material: _materials.GLMaterial | None) -> None:
        """
        Temporarily override this object's own display material.

        Handler classes use this to highlight objects compatible with
        whatever is currently being added/placed (see e.g.
        handlers.bundle_handler._highlight_compatible_wires), and
        objects.wire.Wire.set_selected uses it to show a wire's own
        WireLayouts in the selected color while the layouts themselves
        aren't the true selection (mainframe only ever tracks one true
        selected object at a time).

        An object is only ever identified with one material or the
        other, never both -- passing a new one simply replaces whatever
        is currently showing, independent of is_selected; passing None
        clears the override and falls back to whatever is_selected
        would normally show (see set_selected, whose own _material/
        _is_opaque assignment this mirrors).

        :param material: The material to display this object as, or
            None to clear the override.
        :type material: :class:`_materials.GLMaterial` | None
        """
        if material is not None:
            self._material = material
        elif self._is_selected:
            self._material = self._selected_material
        else:
            self._material = self._unselected_material

        if self._material is None:
            self._is_opaque[0] = 1
        else:
            self._is_opaque[0] = int(self._material.is_opaque)

    @_check_types.do
    def _update_position(self, position: _point.Point):
        """
        Update the position.

        Internal Use.

        :type position: :class:`_point.Point`
        """
        with self.editor.context:
            self._o_position = position.copy()
            self.numpy_position[:] = position.as_numpy

            self._compute_obb()
            self._compute_aabb()

        self.editor.Refresh(False)

    @_check_types.do
    def _update_angle(self, angle: _angle.Angle):
        """
        Update the angle.

        Internal Use.

        :type angle: :class:`_angle.Angle`
        """

        with self.editor.context:
            self._o_angle = angle.copy()
            self._angle_inverse = -angle

            self._compute_obb()
            self._compute_aabb()

        self.editor.Refresh(False)

    @_check_types.do
    def _update_scale(self, scale: _point.Point):
        """
        Update the scale.

        Internal Use.

        :type scale: :class:`_point.Point`
        """

        with self.editor.context:
            self._o_scale = scale.copy()

            self._compute_obb()
            self._compute_aabb()

        self.editor.Refresh(False)

    @property
    @_check_types.do
    def position(self) -> _point.Point:
        """
        Get the position.

        :rtype: :class:`_point.Point`
        """
        return self._position

    @position.setter
    @_check_types.do
    def position(self, value: _point.Point):
        """
        Set the position.

        This is added so a left hand operator (+=, -=, etc...) is able to be used.

        :type value: :class:`_point.Point`
        :raises AttributeError: Raised when the operation cannot be completed.
        """

        if value is not self._position:
            raise AttributeError('Position is only able to be modified not set')

        self._position = value

    @property
    @_check_types.do
    def angle(self) -> _angle.Angle:
        """
        Get the angle.

        :rtype: :class:`_angle.Angle`
        """

        return self._angle

    @angle.setter
    @_check_types.do
    def angle(self, value: _angle.Angle):
        """
        Set the angle.

        This is added so a left hand operator (+=, -=, etc...) is able to be used.

        :type value: :class:`_angle.Angle`
        :raises AttributeError: Raised when the operation cannot be completed.
        """

        if value is not self._angle:
            raise AttributeError('Angle is only able to be modified not set')

        self._angle = value

    @property
    @_check_types.do
    def scale(self) -> _point.Point:
        """
        Get the scale.

        :rtype: :class:`_point.Point`
        """

        return self._scale

    @scale.setter
    @_check_types.do
    def scale(self, value: _point.Point):
        """
        Set the scale.

        This is added so a left hand operator (+=, -=, etc...) is able to be used.

        :type value: :class:`_point.Point`
        :raises AttributeError: Raised when the operation cannot be completed.
        """

        if value is not self._scale:
            raise AttributeError('Scale is only able to be modified not set')

        self._scale = value

    @property
    @_check_types.do
    def obb(self) -> np.ndarray:
        """
        Return the OBB.

        :rtype: :class:`np.ndarray`
        """

        return self._obb

    @property
    @_check_types.do
    def aabb(self) -> np.ndarray:
        """
        Return the AABB.

        :rtype: :class:`np.ndarray`
        """

        return self._aabb

    @property
    @_check_types.do
    def is_selected(self) -> bool:
        """
        Get if the object is selected.

        :returns: True if selected else False
        :rtype: bool
        """

        return self._is_selected

    @_check_types.do
    def set_selected(self, flag: bool):
        """
        Set if the object is selected.

        :param flag: True if selected else False
        :type flag: bool
        """

        if flag:
            self._material = self._selected_material
        else:
            self._material = self._unselected_material

        if self._material is None:
            self._is_opaque[0] = 1
        else:
            self._is_opaque[0] = int(self._material.is_opaque)

        self._is_selected = flag

    @_check_types.do
    def delete(self):
        """
        Execute the delete operation.

        Row deletion and canvas de-registration are handled once, centrally,
        by :meth:`ObjectBase.delete`. Subclasses override this as their hook
        for view-local teardown.
        """

        self.parent.delete()

    @_check_types.do
    def _delete(self):
        """
        Any object specific taredown should occur in this function
        """
        self._is_deleted = True
        self.editor.Refresh()

    @property
    @_check_types.do
    def material(self) -> _materials.GLMaterial:
        """
        Gets the current GL material being used

        :rtype: `_materials.GLMaterial`
        """

        if self._is_selected:
            return self._selected_material

        return self._material

    @property
    @_check_types.do
    def is_opaque(self) -> np.ndarray:
        """
        Get the objects opacity

        :returns: True if object is 100% opaque
        :rtype: `np.ndarray`
        """

        return self._is_opaque

    @_check_types.do
    def get_context_menu(self):  # NOQA
        """
        Get the context menu.

        :returns: Context menu or None
        """

        return None

    @property
    @_check_types.do
    def is_visible(self) -> bool:
        """
        Get object visibility

        :rtype: bool
        """

        raise NotImplementedError

    @is_visible.setter
    @_check_types.do
    def is_visible(self, value: bool):
        """
        Set object visibility.

        :type value: bool
        """

        raise NotImplementedError

    @_check_types.do
    def touching_budgets(self) -> list:
        """
        Return every ``(neighbor_x, neighbor_z, max_length_mm)`` length
        budget constraining how far this object can move, in whichever
        view enforces such a thing (currently only the peg-board view --
        see ``objects.objects_pegboard.chain_edges``).

        Default: no constraints. Overridden by whichever peg-board object
        types actually sit on a wire/bundle chain (anchors touching one
        end, wire-layout/bundle-layout waypoints touching two) -- a
        drag handler clamps its candidate position against every entry
        this returns, independently, never moving anything else (see
        ``drag_handlers.editor_pegboard``'s "it will not pull the things
        that are at the other ends" rule).

        Guaranteed to exist on every object in every view.

        :rtype: list[tuple[float, float, float]]
        """
        return []

    @_check_types.do
    def can_drag(self) -> bool:
        """
        Return whether this object can currently be dragged via the mouse
        in this view.

        Default: True whenever this object has a real position (a
        rendering-presence-only object with ``position is None`` can
        never be dragged). Override to reject dragging outright for a
        specific object type/view (return False -- e.g. a seal, which
        can never be moved by mouse in any view), or to gate on runtime
        state (e.g. a terminal currently seated in a cavity).

        Guaranteed to exist on every object in every view -- canvas-level
        drag dispatch calls this unconditionally, never checking
        ``hasattr``/type first.

        :rtype: bool
        """
        return self._position is not None

    @_check_types.do
    def drag(self, delta: _point.Point) -> None:
        """
        Apply a world-space drag *delta*.

        Default: translate this object's own position directly
        (``self._position += delta``). Override for object-specific
        movement that isn't a plain translation (e.g. a splice/wire-
        marker/wire-service-loop that must follow along a wire instead
        of moving freely -- see the object-type drag rules), or make
        this a no-op when :meth:`can_drag` returns False for this
        type/view combination (the default no-op below already covers
        that case as long as :meth:`can_drag` is also overridden to
        match -- callers are expected to check :meth:`can_drag` first,
        but this stays safe to call unconditionally regardless).

        :param delta: World-space delta to apply this frame.
        :type delta: :class:`_point.Point`
        """
        if self._position is not None:
            self._position += delta

    @_check_types.do
    def can_rotate(self) -> bool:
        """
        Return whether this object can currently be rotated via the
        rotation-ring gizmo in this view.

        Default: True whenever this object has a real angle. Override to
        reject rotation outright for a specific object type/view, or to
        gate on runtime state, mirroring :meth:`can_drag`.

        Guaranteed to exist on every object in every view.

        :rtype: bool
        """
        return self._angle is not None

    @_check_types.do
    def rotate(self, axis: str, value: float) -> None:
        """
        Apply a rotation-drag angle *value* (degrees) to Euler *axis*.

        Default: write straight through to the live
        :class:`~harness_designer.geometry.angle.Angle` (``setattr``) --
        its own bound callbacks already handle everything else (DB
        write, cascades, geometry refresh). Override as a no-op (or to
        reject/clamp) when this view/type combination doesn't support
        rotation the way the generic default assumes -- pair with a
        matching :meth:`can_rotate` override so the gizmo is never even
        offered in the first place.

        :param axis: ``'x'``, ``'y'`` or ``'z'``.
        :type axis: str
        :param value: New Euler value in degrees.
        :type value: float
        """
        if self._angle is not None:
            setattr(self._angle, axis, value)

    @_check_types.do
    def _render_geometry(self, pos_loc, rot_loc, scale_loc, normal_loc=None):
        """Render the object geometry using the active shader program.

        Called by render() for each rendering pass (faces, edges, normals, vertices).
        This object's own transform (position/rotation/scale) and the uniform
        locations to set them at are handed straight to the VBO's own
        render() -- the VBO owns setting those uniforms (and, for a compound
        handler like shapes/text.py's Text, deriving whatever per-piece
        values it actually needs from this single transform) rather than
        this method setting them itself before an argument-less draw call.
        """

        if self._vbo is None:
            return

        self._vbo.render(
            pos_loc, rot_loc, scale_loc, normal_loc,
            self._position, self._angle, self._scale, self.smooth)

    def _render_selected(self):
        pass

    @_check_types.do
    def render(self, faces_program, edges_program, vertices_program):
        """
        Execute the render operation.

        :param faces_program: Value for ``faces_program``.
        :type faces_program: UNKNOWN

        :param edges_program: Value for ``edges_program``.
        :type edges_program: UNKNOWN

        :param vertices_program: Value for ``vertices_program``.
        :type vertices_program: UNKNOWN
        """

        if not self.is_visible:
            return

        if self._vbo is None:
            return

        if self._vbo.is_dirty:
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

            self._render_geometry(pos_loc, rot_loc, scale_loc, normal_loc)
            GL.glUseProgram(0)

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

            self._render_geometry(pos_loc, rot_loc, scale_loc, normal_loc)

            GL.glUseProgram(0)

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

            self._render_geometry(pos_loc, rot_loc, scale_loc, normal_loc)
            GL.glUseProgram(0)

        if _debug_config.draw_vertices:
            GL.glUseProgram(vertices_program)

            pos_loc = GL.glGetUniformLocation(vertices_program, "objectPosition")
            rot_loc = GL.glGetUniformLocation(vertices_program, "objectRotation")
            scale_loc = GL.glGetUniformLocation(vertices_program, "objectScale")
            vertex_color_loc = GL.glGetUniformLocation(vertices_program, "vertexColor")

            GL.glUniform3f(vertex_color_loc, *_debug_config.vertices_color)  # Red vertices

            self._render_geometry(pos_loc, rot_loc, scale_loc)

            GL.glUseProgram(0)

        if self.is_selected:
            self._render_selected()

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

