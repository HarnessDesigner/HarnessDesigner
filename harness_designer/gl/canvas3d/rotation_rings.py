# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Rotation ring gizmo for mouse-driven angle changes.

Right-clicking a selected object shows three rings (one per Euler axis), each
with a grab handle. Dragging a handle locks rotation to that axis and
increments/decrements the matching Euler angle directly — the quaternion is
only ever rebuilt from the Euler angles, never read back (see the Euler rule
in CODEBASE_MAP.md).

Ring planes follow the nested Euler order used by
``Quaternion.from_euler`` (effective matrix ``Ry·Rx·Rz``, i.e. Z innermost,
X middle, Y outermost — verified numerically):

- y ring: fixed in world space (normal = world Y)
- x ring: normal = Ry @ X
- z ring: normal = Ry·Rx @ Z (full rotation applied to Z)
"""

import math
import ctypes
from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from ...shapes import torus as _torus
from ...shapes import sphere as _sphere
from ...objects.objects3d import base3d as _base3d
from ...objects.objects2d import base2d as _base2d
from ...objects import object_base as _object_base
from ...geometry import point as _point
from ...geometry import angle as _angle
from ...gl import materials as _materials
from ... import utils as _utils
from ... import color as _color
from ... import config as _config


Config = _config.Config.editor3d


if TYPE_CHECKING:
    from . import canvas as _canvas
    from ... import ui as _ui
    from ... import objects as _objects


# Pixel tolerance used when picking a grab handle
HANDLE_PICK_TOLERANCE = 14.0

# Tessellation of the ring torus (segments around the ring / around the tube)
RING_RESOLUTION = (128, 16)

# Vertical subdivisions of the handle sphere
HANDLE_RESOLUTION = 24

AXES = ('x', 'y', 'z')

# Unit direction (in ring-local space, ring lies in the XY plane) where each
# axis ring places its grab handle. Chosen so the three handles land on
# distinct world axes (x→+Y, y→+Z, z→+X) when the object has no rotation
# applied.
HANDLE_LOCAL_DIRS = {
    'x': np.array([0.0, 1.0, 0.0], dtype=np.float32),
    'y': np.array([0.0, -1.0, 0.0], dtype=np.float32),
    'z': np.array([1.0, 0.0, 0.0], dtype=np.float32),
}


def _build_ring_mesh(tube_diameter_scale: float) -> tuple[np.ndarray, int]:
    """Build the radius-1.0 ring mesh with the configured tube thickness.

    :returns: ``(packed, count)`` — the single packed array
        (positions / smooth normals / face normals end to end) the shader
        pipeline expects, plus the triangle-soup vertex count.
    """
    # tube diameter / ring diameter == tube radius / ring radius, so the
    # config ratio can be used directly as the tube radius of a unit ring
    vertices, faces = _torus.create(
        1.0, max(float(tube_diameter_scale), 1e-4), *RING_RESOLUTION)
    return _utils.compute_normals(vertices, faces)


def _build_handle_mesh() -> tuple[np.ndarray, int]:
    """Build the unit-diameter handle sphere mesh."""
    vertices, faces = _sphere.create(0.5, resolution=HANDLE_RESOLUTION)
    return _utils.compute_normals(vertices, faces)


def _data_views(packed: np.ndarray, count: int) -> list:
    """Slice a packed mesh into the ``Base3D._data`` block layout."""
    n = count * 3
    return [packed[0:n], packed[n:2 * n], packed[2 * n:3 * n], count]


class _GizmoBuffer:
    """A private single-buffer mesh outside the managed VBO arena.

    The shader pipeline reads all three vertex attributes from ONE buffer
    at byte offsets (positions / smooth normals / face normals packed end
    to end), with the offsets baked into a VAO — the same layout
    :class:`gl.vbo.PooledVBOHandler` uses. The gizmo owns its own small buffer
    instead of an arena allocation so dimension config changes can
    re-upload the mesh in real time without buffer-pool management.

    GL objects are created lazily inside ``draw()`` (the context is current
    during rendering) and re-created after every mesh update.
    """

    def __init__(self, packed: np.ndarray, count: int):
        # full copy — _data views into the same array are exposed to Base3D
        # bookkeeping and must never alias the upload data
        self._packed = np.array(packed, dtype=np.float32, copy=True)
        self.count = int(count)

        self._buffer = None
        self._vao = None
        self._dirty = True

    def update(self, packed: np.ndarray, count: int):
        """Replace the mesh; the GPU re-upload happens on the next draw."""
        self._packed = np.array(packed, dtype=np.float32, copy=True)
        self.count = int(count)
        self._dirty = True

    def _upload(self):
        """(Re)upload the packed mesh and bake the VAO offsets."""
        if self._buffer is None:
            self._buffer = GL.glGenBuffers(1)

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, self._packed.nbytes,
                        self._packed, GL.GL_DYNAMIC_DRAW)

        if self._vao is None:
            self._vao = GL.glGenVertexArrays(1)

        block = self.count * 3 * self._packed.itemsize

        GL.glBindVertexArray(self._vao)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._buffer)

        GL.glEnableVertexAttribArray(0)
        GL.glVertexAttribPointer(0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p(0))

        GL.glEnableVertexAttribArray(1)
        GL.glVertexAttribPointer(1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p(block))

        GL.glEnableVertexAttribArray(2)
        GL.glVertexAttribPointer(2, 3, GL.GL_FLOAT, GL.GL_FALSE, 0,
                                 ctypes.c_void_p(2 * block))

        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, 0)
        GL.glBindVertexArray(0)

        self._dirty = False

    def draw(self):
        """Bind the VAO and issue the draw call (GL context must be current)."""
        if self._dirty:
            self._upload()

        GL.glBindVertexArray(self._vao)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self.count)
        GL.glBindVertexArray(0)

    def delete(self):
        """Free the GL objects (GL context must be current)."""
        if self._vao is not None:
            try:
                GL.glDeleteVertexArrays(1, [self._vao])
            except Exception:  # NOQA
                pass
            self._vao = None

        if self._buffer is not None:
            try:
                GL.glDeleteBuffers(1, [self._buffer])
            except Exception:  # NOQA
                pass
            self._buffer = None

        self._dirty = True


def wrap_angle(value: float) -> float:
    """Wrap an angle in degrees to the ``-180..180`` UI range."""
    return ((value + 180.0) % 360.0) - 180.0


def validate_snap_angle(value) -> float:
    """Return a usable snap angle, or ``0.0`` (disabled) when invalid.

    A snap angle is valid when it is positive, has at most 2 decimal places,
    and divides the 360 degree range evenly — which together guarantee every
    snapped multiple also lands on at most 2 decimal places. The check is
    done in integer hundredths to avoid float fuzz: ``36000 % (value*100)``.

    :param value: Candidate snap angle in degrees.
    :returns: The validated snap angle, or ``0.0`` when snapping is disabled
        or the value is invalid.
    :rtype: float
    """
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0

    if v <= 0.0:
        return 0.0

    hundredths = round(v * 100.0)

    # more than 2 decimal places
    if abs(v * 100.0 - hundredths) > 1e-6:
        return 0.0

    # must divide the 360 degree range evenly
    if hundredths == 0 or 36000 % hundredths != 0:
        return 0.0

    return hundredths / 100.0


def slot_ring_angle(axis: str, euler: list) -> "_angle.Angle":
    """Return the orientation that maps the ring (XY plane) onto ``axis``.

    The Euler slots are nested (effective matrix ``Ry·Rx·Rz``), so each
    ring's plane depends on the angles applied outside of it. Each ring also
    spins with its own slot's angle so the grab handle tracks the drag.

    :param axis: ``'x'``, ``'y'`` or ``'z'``.
    :param euler: Current ``[x, y, z]`` Euler angles in degrees.
    """
    ex, ey, ez = euler

    if axis == 'x':
        return _angle.Angle.from_euler(0.0, ey + 90.0, ex)

    if axis == 'y':
        return _angle.Angle.from_euler(-90.0, ey, 0.0)

    return _angle.Angle.from_euler(ex, ey, ez)


def slot_normal(axis: str, euler: list) -> np.ndarray:
    """Return the world-space rotation axis for an Euler slot.

    Incrementing an Euler angle rotates the object about this axis given the
    nesting order of ``Quaternion.from_euler``.

    :param axis: ``'x'``, ``'y'`` or ``'z'``.
    :param euler: Current ``[x, y, z]`` Euler angles in degrees.
    """
    ex, ey, _ = euler

    if axis == 'x':
        a = _angle.Angle.from_euler(0.0, ey, 0.0)
        return a @ np.array([1.0, 0.0, 0.0], dtype=np.float32)

    if axis == 'z':
        a = _angle.Angle.from_euler(ex, ey, 0.0)
        return a @ np.array([0.0, 0.0, 1.0], dtype=np.float32)

    return np.array([0.0, 1.0, 0.0], dtype=np.float32)


class RotationRings(_object_base.ObjectBase):
    """Rotation gizmo shown around a selected object in angle mode."""

    def __init__(self, canvas: "_canvas.Canvas", selected: "_objects.ObjectBase"):
        """Initialise the :class:`RotationRings` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        :param selected: The selected object the rings surround.
        :type selected: :class:`_objects.ObjectBase`
        """
        mainframe = canvas.mainframe

        _object_base.ObjectBase.__init__(self, mainframe, None)
        self.selected = selected
        self.obj2d = Rings2D(self)
        self.obj3d = Rings3D(self, selected, mainframe)
        self._treeitem = None
        self.mainframe.add_object(self)

    def set_treeitem(self, treeitem):
        """Set the treeitem.

        :param treeitem: Value for ``treeitem``.
        :type treeitem: UNKNOWN
        """
        self._treeitem = treeitem

    def get_treeitem(self):
        """Return the treeitem.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._treeitem

    def pick_handle(self, mouse_pos: _point.Point, camera) -> str | None:
        """Return the axis of the grab handle under the mouse, if any.

        :param mouse_pos: Mouse position in screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        :param camera: Canvas camera used for projection.
        :returns: ``'x'``, ``'y'`` or ``'z'`` when a handle is hit, else ``None``.
        :rtype: str | None
        """
        best_axis = None
        best_depth = math.inf

        for axis in AXES:
            handle_world = self.obj3d.handle_position(axis)
            screen = camera.ProjectPoint(handle_world)

            dx = float(screen.x) - float(mouse_pos.x)
            dy = float(screen.y) - float(mouse_pos.y)
            dist = math.sqrt(dx * dx + dy * dy)

            if dist <= HANDLE_PICK_TOLERANCE and float(screen.z) < best_depth:
                best_depth = float(screen.z)
                best_axis = axis

        return best_axis

    def __del__(self):
        """Execute the del operation."""
        self.delete()

    def delete(self):
        """Remove the gizmo from both editors and unbind from the object."""
        self.obj3d.detach()
        self.mainframe.remove_object(self)

    def close(self):
        """Execute the close operation.

        :raises NotImplementedError: Raised when the operation cannot be completed.
        """
        raise NotImplementedError

    def set_selected(self, flag):
        """Set the selected.

        :param flag: Value for ``flag``.
        :type flag: UNKNOWN
        """
        pass

    @property
    def is_selected(self) -> bool:
        """Return the is selected.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return False

    @is_selected.setter
    def is_selected(self, value: bool):
        """Set the is selected.

        :param value: Value to store or process.
        :type value: bool
        """
        pass


class Rings2D(_base2d.Base2D):
    """2D placeholder for the rotation ring gizmo (3D editor only)."""

    def __init__(self, parent):
        """Initialise the :class:`Rings2D` instance.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        angle = _angle.Angle()
        position = _point.Point(0, 0)

        _base2d.Base2D.__init__(self, parent, None, position, angle)

    def set_selected(self, flag: bool):
        """Set the selected.

        :param flag: Value for ``flag``.
        :type flag: bool
        """
        pass

    @property
    def is_selected(self) -> bool:
        """Return the is selected.

        :returns: Property value. UNKNOWN details.
        :rtype: bool
        """
        return False


class Rings3D(_base3d.Base3D):
    """Render three Euler-axis rings with grab handles around an object."""

    def __init__(self, parent, selected: "_objects.ObjectBase",
                 mainframe: "_ui.MainFrame"):
        """Initialise the :class:`Rings3D` instance.

        :param parent: Parent :class:`RotationRings` wrapper.
        :param selected: The object being rotated.
        :param mainframe: MainFrame reference.
        """
        obj3d = selected.obj3d

        # Private single-buffer meshes outside the managed VBO arena — no GL
        # context required to build them, and dimension config changes can
        # rebuild + re-upload them in real time
        ring_packed, ring_count = _build_ring_mesh(
            Config.rotation_rings.tube_diameter_scale)
        handle_packed, handle_count = _build_handle_mesh()

        self._ring_buf = _GizmoBuffer(ring_packed, ring_count)
        self._handle_buf = _GizmoBuffer(handle_packed, handle_count)

        # Base3D uses _data (vbo=None path) for its aabb/obb bookkeeping
        self._ring_mesh = _data_views(ring_packed, ring_count)

        # Plastic is a lit material so the rings shade with the scene
        # lights (Glowing is emissive/flat — fine for arrows, ugly on tubes).
        # Colors come from config as scalar RGBA lists; Color converts
        # float channels to 0-255 automatically.
        self._build_materials()

        self._obj3d = obj3d
        self._radius = 1e-3
        self._handle_scale = 1e-3
        self._compute_size()

        # Signature of the config values baked into materials/meshes —
        # render() dirty-checks this each frame so config edits made from
        # UI controls apply live (no dependency on ConfigDB.bind)
        self._config_sig = self._current_config_sig()

        self._ring_quats = {}
        self._handle_positions = {}

        # Track angle and scale changes made from UI controls while the
        # rings are visible. The position is NOT copied — the gizmo shares
        # the object's Point instance, so it is always exactly centered on
        # the object with no follow-the-leader callback needed.
        obj_angle = obj3d.angle
        obj_scale = obj3d.scale

        obj_angle.bind(self._on_obj_angle)
        self._obj_angle = obj_angle

        obj_scale.bind(self._on_obj_scale)
        self._obj_scale = obj_scale

        scale = _point.Point(1.0, 1.0, 1.0)
        angle = _angle.Angle.from_euler(0, 0, 0)
        material = self._ring_materials['z']

        # _floor_guard defeats Base3D.__init__'s inline floor-lock check —
        # with a shared position instance a bump would move the actual
        # object (and write it to the database)
        self._floor_guard = True

        _base3d.Base3D.__init__(self, parent, None, None,
                                angle, obj3d.position, scale, material,
                                data=self._ring_mesh)

        self._floor_guard = False
        self._is_visible = True

        self._compute_obb()
        self._compute_aabb()

        self._update_rings()

    def _build_materials(self):
        """(Re)build the per-axis materials from the config colors."""
        ring_config = Config.rotation_rings
        self._ring_materials = {
            axis: _materials.Plastic(
                _color.Color(*getattr(ring_config, f'{axis}_color')))
            for axis in AXES
        }

    @staticmethod
    def _current_config_sig() -> tuple:
        """Return a comparable snapshot of the gizmo-affecting config."""
        ring_config = Config.rotation_rings
        return (
            float(ring_config.diameter_scale),
            float(ring_config.handle_diameter_scale),
            float(ring_config.tube_diameter_scale),
            tuple(ring_config.x_color),
            tuple(ring_config.y_color),
            tuple(ring_config.z_color),
        )

    def _refresh_from_config(self):
        """Re-apply config-driven properties after a config change."""
        old_sig = self._config_sig
        self._config_sig = self._current_config_sig()

        # tube thickness is baked into the mesh — rebuild only when changed
        if old_sig[2] != self._config_sig[2]:
            packed, count = _build_ring_mesh(self._config_sig[2])
            self._ring_buf.update(packed, count)

            self._ring_mesh = _data_views(packed, count)
            self._data = self._ring_mesh

        if old_sig[3:] != self._config_sig[3:]:
            self._build_materials()

        self._compute_size()
        self._update_rings()

    def _update_position(self, position: _point.Point):
        """Track gizmo position changes WITHOUT Base3D's world-space logic.

        The base implementation re-applies the floor lock (which would bump
        the gizmo off-center — its local mesh always dips below ground) and
        shifts ``_data`` by the position delta (the legacy world-space
        client-array semantics). The gizmo's mesh is local space with the
        transform done in uniforms, so neither applies.
        """
        self._o_position = position.copy()
        self.numpy_position[:] = position.as_numpy

        self._compute_obb()
        self._compute_aabb()

    def _compute_aabb(self):
        """Mirror the tracked object's AABB.

        The culling rows hold live views of ``self._aabb``, so keeping it
        identical to the object's box links the gizmo's view culling to the
        object: the rings are culled if and only if the object is.
        """
        obj_aabb = self._obj3d.aabb

        for i in range(2):
            for j in range(3):
                self._aabb[i][j] = obj_aabb[i][j]

        if self._floor_guard:
            # During Base3D.__init__ only: report the bottom at/above the
            # ground plane so the inline floor-lock check can never fire
            # and move the shared object position
            ground = float(Config.floor.ground_height)
            if self._aabb[0][1] < ground:
                self._aabb[0][1] = ground

    def _compute_obb(self):
        """Mirror the tracked object's OBB (culling linked to the object)."""
        self._obb = np.array(self._obj3d.obb, dtype=np.float32, copy=True)

    def detach(self):
        """Unbind from the tracked object and free the GL buffers."""
        # the position is the object's own Point instance — Base3D bound our
        # _update_position to it, so it must be released explicitly
        self._position.unbind(self._update_position)
        self._obj_angle.unbind(self._on_obj_angle)
        self._obj_scale.unbind(self._on_obj_scale)

        try:
            with self.editor3d.context:
                self._ring_buf.delete()
                self._handle_buf.delete()
        except Exception:  # NOQA
            # Context may be unavailable during shutdown — the buffers die
            # with the context in that case
            pass

    def _compute_size(self):
        """Derive ring/handle sizing from the object's AABB space diagonal.

        All gizmo sizing derives from the AABB space diagonal (the largest
        distance between two points of the box) so the rings always clear
        the object regardless of its proportions. The tube thickness
        follows automatically: the ring mesh is radius 1.0 with a
        config-driven tube ratio, rendered with a uniform scale.
        """
        aabb = self._obj3d.aabb
        diagonal = float(np.linalg.norm(
            np.asarray(aabb[1], dtype=np.float64) -
            np.asarray(aabb[0], dtype=np.float64)))

        ring_config = Config.rotation_rings
        diameter = diagonal * float(ring_config.diameter_scale)

        self._radius = max(diameter / 2.0, 1e-3)
        # The sphere VBO has a diameter of 1.0, so the scale factor IS the
        # world diameter of the handle
        self._handle_scale = diameter * float(ring_config.handle_diameter_scale)

    def apply_drag_angle(self, axis: str, value: float):
        """Write a drag-driven Euler value without re-triggering ourselves.

        The angle callback is unbound around the write (the same pattern the
        UI property controls use) so the rings do not respond to their own
        updates; the ring geometry is refreshed explicitly afterwards.

        :param axis: ``'x'``, ``'y'`` or ``'z'``.
        :param value: New Euler value in degrees.
        """
        self._obj_angle.unbind(self._on_obj_angle)
        try:
            setattr(self._obj_angle, axis, value)
        finally:
            self._obj_angle.bind(self._on_obj_angle)

        self._update_rings()

    def handle_position(self, axis: str) -> _point.Point:
        """Return the world position of the grab handle for ``axis``.

        :param axis: ``'x'``, ``'y'`` or ``'z'``.
        :returns: Handle position in world space.
        :rtype: :class:`_point.Point`
        """
        offset = self._handle_positions[axis]
        return _point.Point(
            float(self._position.x) + float(offset[0]),
            float(self._position.y) + float(offset[1]),
            float(self._position.z) + float(offset[2]),
        )

    def _update_rings(self):
        """Recompute ring orientations and handle offsets from the Euler angles."""
        euler = self._obj_angle.as_euler_float

        for axis in AXES:
            ring_angle = slot_ring_angle(axis, euler)
            self._ring_quats[axis] = ring_angle.as_quat_numpy.tolist()

            local_dir = HANDLE_LOCAL_DIRS[axis]
            world_dir = ring_angle @ local_dir
            self._handle_positions[axis] = np.asarray(world_dir, dtype=np.float32) * self._radius


    def _on_obj_angle(self, _):
        """Update ring orientations when the tracked object rotates."""
        self._update_rings()

    def _on_obj_scale(self, _):
        """Resize the gizmo when the tracked object's scale changes.

        Base3D's own scale callback was bound first, so the object's AABB
        has already been recomputed by the time this runs.
        """
        self._compute_size()
        self._update_rings()

    def render(self, faces_program, edges_program, vertices_program):
        """Render the three rings and their grab handles."""
        # Live config tracking: rebuild sizing/mesh/materials when any of
        # the gizmo settings changed since the last frame
        if self._config_sig != self._current_config_sig():
            self._refresh_from_config()

        GL.glUseProgram(faces_program)

        pos_loc = GL.glGetUniformLocation(faces_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(faces_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(faces_program, "objectScale")

        # Smooth normals so the tube cross-section shades as a round surface
        normal_loc = GL.glGetUniformLocation(faces_program, "normalMode")
        if normal_loc != -1:
            GL.glUniform1i(normal_loc, 0)

        # The gizmo is a UI element, not part of the scene — suppress the
        # floor reflection for it, then restore the global config value so
        # objects rendered after the rings keep theirs.
        reflect_loc = GL.glGetUniformLocation(faces_program, "objectHasReflection")
        if reflect_loc != -1:
            GL.glUniform1i(reflect_loc, 0)

        position = self._position.as_float

        for axis in AXES:
            self._ring_materials[axis].set(faces_program)

            # Ring
            GL.glUniform3f(pos_loc, *position)
            GL.glUniform4f(rot_loc, *self._ring_quats[axis])
            GL.glUniform3f(scale_loc, self._radius, self._radius, self._radius)
            self._ring_buf.draw()

            # Grab handle
            handle = self.handle_position(axis)
            GL.glUniform3f(pos_loc, *handle.as_float)
            GL.glUniform4f(rot_loc, 1.0, 0.0, 0.0, 0.0)
            GL.glUniform3f(scale_loc, self._handle_scale,
                           self._handle_scale, self._handle_scale)
            self._handle_buf.draw()

        if reflect_loc != -1:
            config = self.editor3d.config
            GL.glUniform1i(reflect_loc, int(
                config.floor.reflections.enable and
                config.floor.enable_floor_lock))


class DragRotate:
    """Rotate a selected object about one locked Euler axis with the mouse.

    The drag measures the screen-space angle of the cursor around the
    object's projected center and accumulates the change into the locked
    axis's Euler angle. The Euler value is the only thing written — the
    quaternion is rebuilt from it by :class:`_angle.Angle`.
    """

    def __init__(self, canvas: "_canvas.Canvas",
                 selected: "_objects.ObjectBase", axis: str,
                 rings: "RotationRings"):
        """Initialise the :class:`DragRotate` instance.

        :param canvas: Canvas instance.
        :type canvas: :class:`_canvas.Canvas`
        :param selected: The object being rotated.
        :type selected: :class:`_objects.ObjectBase`
        :param axis: The locked Euler axis (``'x'``, ``'y'`` or ``'z'``).
        :type axis: str
        :param rings: The active gizmo — angle writes go through its
            loop-safe :meth:`Rings3D.apply_drag_angle`.
        :type rings: :class:`RotationRings`
        """
        self.canvas = canvas
        self.selected = selected
        self.axis = axis
        self.rings = rings


        obj3d = selected.obj3d
        self.angle = obj3d.angle

        self.start_value = float(getattr(self.angle, axis))

        center_screen = canvas.camera.ProjectPoint(obj3d.position)
        self._cx = float(center_screen.x)
        self._cy = float(center_screen.y)

        # Drag direction sign: positive Euler rotation appears counter-
        # clockwise on screen when the rotation axis points at the camera.
        normal = slot_normal(axis, self.angle.as_euler_float)
        to_camera = (canvas.camera.position - obj3d.position).as_numpy
        facing = float(np.dot(normal, np.asarray(to_camera[:3], dtype=np.float32)))
        self._sign = 1.0 if facing >= 0.0 else -1.0

        self._prev_phi = None
        self._total = 0.0

    def _screen_phi(self, mouse_pos: _point.Point) -> float:
        """Return the math-orientation angle of the cursor around the center."""
        # Screen y grows downward; negate for counter-clockwise-positive math
        return math.atan2(-(float(mouse_pos.y) - self._cy),
                          float(mouse_pos.x) - self._cx)

    def __call__(self, mouse_pos: _point.Point):
        """Update the locked Euler angle from the current mouse position.

        :param mouse_pos: Mouse position in screen coordinates.
        :type mouse_pos: :class:`_point.Point`
        """
        phi = self._screen_phi(mouse_pos)

        if self._prev_phi is None:
            self._prev_phi = phi
            return

        # Wrap-safe incremental step so crossing the atan2 seam doesn't jump
        step = math.atan2(math.sin(phi - self._prev_phi),
                          math.cos(phi - self._prev_phi))
        self._prev_phi = phi
        self._total += step

        new_value = wrap_angle(
            self.start_value + self._sign * math.degrees(self._total))

        # The snap/detent settings are read on every mouse event (not cached
        # at drag start) so toolbar/config changes apply in real time, even
        # mid-drag
        ring_config = Config.rotation_rings

        if ring_config.snap_enable:
            snap = validate_snap_angle(ring_config.snap_angle)
        else:
            snap = 0.0

        if snap:
            # Quantize to the snap increment; the validator guarantees every
            # multiple has at most 2 decimal places, the round() just clears
            # float fuzz from the division. Snapping replaces the 0.0
            # detent — the increments provide their own stops.
            new_value = wrap_angle(
                round(round(new_value / snap) * snap, 2))

        elif abs(new_value) <= max(float(ring_config.detent_width), 0.0):
            # Detent: stick at exactly 0.0 until the drag moves past the zone
            new_value = 0.0

        self.rings.obj3d.apply_drag_angle(self.axis, new_value)
