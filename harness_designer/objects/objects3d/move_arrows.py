import math
from typing import TYPE_CHECKING

import numpy as np
from OpenGL import GL

from . import base3d as _base3d
from ...geometry import angle as _angle
from ...geometry import point as _point
from ... import color as _color
from ...gl import materials as _materials

if TYPE_CHECKING:
    from ... import ui as _ui


# Configurable scaling factors for arrow sizing
ARROW_LENGTH_SCALE = 1.5
ARROW_RADIUS_SCALE = 0.05
CONE_LENGTH_SCALE = 0.15
CONE_RADIUS_SCALE = 0.1
ARROW_MARGIN_SCALE = 0.1

_SEGMENTS = 16


class _ArrowParent:
    """Minimal parent object for Base3D initialization."""

    def __init__(self, mainframe: "_ui.MainFrame"):
        self.mainframe = mainframe


class MoveArrows(_base3d.Base3D):
    """
    Visual feedback arrow displayed while dragging an object.

    Shows a bidirectional arrow (cylinder shaft with cones on both ends) in
    cyan, positioned above or beside the object based on the locked axis.
    The arrow automatically follows the object as it moves.

    This object has no database representation - it is purely visual feedback
    that is alive only as long as the drag operation is active.
    """

    is_selected = False

    def __init__(self, position: _point.Point, axis: str,
                 mainframe: "_ui.MainFrame", aabb: np.ndarray):
        """
        Parameters
        ----------
        position:
            The Point instance from the object being dragged.  A callback is
            registered to this point so the arrow automatically follows the
            object.
        axis:
            'x', 'y', or 'z' - the locked axis of travel.
        mainframe:
            MainFrame reference used to access the editor and add the arrow to
            the rendering pipeline.
        aabb:
            The object's axis-aligned bounding box ``[[xmin,ymin,zmin],
            [xmax,ymax,zmax]]`` used to size and position the arrow.
        """
        width = float(aabb[1][0] - aabb[0][0])
        height = float(aabb[1][1] - aabb[0][1])
        depth = float(aabb[1][2] - aabb[0][2])
        max_dim = max(width, height, depth)

        margin = max_dim * ARROW_MARGIN_SCALE

        if axis in ('x', 'z'):
            # Place arrow above the object - movement is along the floor
            offset = _point.Point(0.0, height / 2.0 + margin, 0.0)
        else:
            # axis == 'y': place arrow to the side - vertical movement, avoids floor
            offset = _point.Point(width / 2.0 + margin, 0.0, 0.0)

        self._tracked_offset = offset

        # Initial world position of the arrow
        init_pos = _point.Point(
            float(position.x) + float(offset.x),
            float(position.y) + float(offset.y),
            float(position.z) + float(offset.z),
        )

        verts, nrmls, count = self._generate_arrow_geometry(init_pos, axis, max_dim)

        identity_angle = _angle.Angle()
        unit_scale = _point.Point(1.0, 1.0, 1.0)

        cyan = _color.Color(0, 255, 255, 255)
        material = _materials.Generic(cyan)

        parent = _ArrowParent(mainframe)

        _base3d.Base3D.__init__(
            self, parent, None, None,
            identity_angle, init_pos, unit_scale, material,
            data=[verts, nrmls, count],
        )

        # Base3D sets _is_visible=False when db_obj is None; correct that here
        self._is_visible = True

        # Maintain float32 render copies updated incrementally in _update_position
        self._render_verts = np.ascontiguousarray(verts, dtype=np.float32)
        self._render_nrmls = np.ascontiguousarray(nrmls, dtype=np.float32)

        # Track the dragged object's position
        position.bind(self._on_position_changed)

        # Register with the 3D rendering pipeline only
        # (not added via mainframe.add_object to avoid the 2D editor, which
        # requires obj2d and does not apply to purely visual feedback objects)
        mainframe.editor3d.add_object(self)

    # ------------------------------------------------------------------
    # Canvas interface
    # ------------------------------------------------------------------

    @property
    def obj3d(self):
        """Return self so this object satisfies the canvas obj.obj3d interface."""
        return self

    # ------------------------------------------------------------------
    # Position tracking
    # ------------------------------------------------------------------

    def _on_position_changed(self, new_position: _point.Point):
        """Called when the tracked object moves; repositions the arrow."""
        target_x = float(new_position.x) + float(self._tracked_offset.x)
        target_y = float(new_position.y) + float(self._tracked_offset.y)
        target_z = float(new_position.z) + float(self._tracked_offset.z)

        curr_x = float(self._position.x)
        curr_y = float(self._position.y)
        curr_z = float(self._position.z)

        dx = target_x - curr_x
        dy = target_y - curr_y
        dz = target_z - curr_z

        if dx != 0.0 or dy != 0.0 or dz != 0.0:
            self._position += _point.Point(dx, dy, dz)

    # ------------------------------------------------------------------
    # Base3D overrides
    # ------------------------------------------------------------------

    def _update_position(self, position: _point.Point):
        """Update geometry when the arrow's own position changes."""
        dx = float(position.x) - float(self._o_position.x)
        dy = float(position.y) - float(self._o_position.y)
        dz = float(position.z) - float(self._o_position.z)

        delta = np.array([dx, dy, dz], dtype=np.float64)
        delta_f32 = delta.astype(np.float32)

        self._data[0] += delta
        self._render_verts += delta_f32

        self._compute_obb()
        self._compute_aabb()

        self._o_position = position.copy()
        self.numpy_position = position.as_numpy

        self.editor3d.Refresh(False)

    def set_selected(self, flag: bool):
        """Arrow is never selectable; intentional no-op."""

    def delete(self):
        """No database object to delete.

        Callback cleanup is handled automatically: ``Point.bind`` stores a
        ``weakref.WeakMethod``, so when this instance is garbage collected the
        position callback is removed from the tracked object's Point without
        any explicit action here.
        """

    def get_context_menu(self):
        """No context menu for arrows."""
        return None

    def render(self, shader_program):
        if not self._is_visible:
            return

        self.material.set(shader_program)

        pos_loc = GL.glGetUniformLocation(shader_program, "objectPosition")
        rot_loc = GL.glGetUniformLocation(shader_program, "objectRotation")
        scale_loc = GL.glGetUniformLocation(shader_program, "objectScale")
        objectHasReflectionLoc = GL.glGetUniformLocation(
            shader_program, "objectHasReflection")

        GL.glUniform1i(objectHasReflectionLoc, 0)
        GL.glUniform3f(pos_loc, 0.0, 0.0, 0.0)
        GL.glUniform4f(rot_loc, 1.0, 0.0, 0.0, 0.0)
        GL.glUniform3f(scale_loc, 1.0, 1.0, 1.0)

        GL.glEnableVertexAttribArray(0)
        GL.glEnableVertexAttribArray(1)

        GL.glVertexAttribPointer(
            0, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, self._render_verts)
        GL.glVertexAttribPointer(
            1, 3, GL.GL_FLOAT, GL.GL_FALSE, 0, self._render_nrmls)

        GL.glDrawArrays(GL.GL_TRIANGLES, 0, self._data[2])

        GL.glDisableVertexAttribArray(0)
        GL.glDisableVertexAttribArray(1)

    # ------------------------------------------------------------------
    # Geometry generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_arrow_geometry(center_pos: _point.Point, axis: str,
                                 max_dim: float) -> tuple:
        """
        Generate bidirectional arrow geometry along the specified axis.

        The arrow consists of a cylinder shaft with a cone on each end.
        Geometry is first built along the Z axis then rotated to align with
        ``axis`` and finally translated to ``center_pos``.

        Returns
        -------
        tuple
            ``(vertices, normals, count)`` where vertices and normals are
            float64 numpy arrays of shape ``(count, 3)``.
        """
        arrow_length = max_dim * ARROW_LENGTH_SCALE
        shaft_radius = max_dim * ARROW_RADIUS_SCALE
        cone_length = max_dim * CONE_LENGTH_SCALE
        cone_radius = max_dim * CONE_RADIUS_SCALE

        shaft_half = arrow_length / 2.0

        cos_a = [math.cos(2.0 * math.pi * i / _SEGMENTS) for i in range(_SEGMENTS)]
        sin_a = [math.sin(2.0 * math.pi * i / _SEGMENTS) for i in range(_SEGMENTS)]

        vertices = []
        normals = []

        # ---- Cylinder shaft ----
        for i in range(_SEGMENTS):
            j = (i + 1) % _SEGMENTS

            x0, y0 = shaft_radius * cos_a[i], shaft_radius * sin_a[i]
            x1, y1 = shaft_radius * cos_a[j], shaft_radius * sin_a[j]

            nx0, ny0 = cos_a[i], sin_a[i]
            nx1, ny1 = cos_a[j], sin_a[j]

            # Two triangles per strip segment
            vertices.extend([
                [x0, y0, -shaft_half], [x1, y1, -shaft_half], [x1, y1, shaft_half],
                [x0, y0, -shaft_half], [x1, y1,  shaft_half], [x0, y0, shaft_half],
            ])
            normals.extend([
                [nx0, ny0, 0], [nx1, ny1, 0], [nx1, ny1, 0],
                [nx0, ny0, 0], [nx1, ny1, 0], [nx0, ny0, 0],
            ])

        # ---- Cones ----
        # Outward normal angle along the cone surface
        side_r = cone_length / math.sqrt(cone_radius ** 2 + cone_length ** 2)
        side_z = cone_radius / math.sqrt(cone_radius ** 2 + cone_length ** 2)

        for sign, base_z, tip_z, nz_dir in (
            (+1, shaft_half, shaft_half + cone_length, side_z),
            (-1, -shaft_half, -shaft_half - cone_length, -side_z),
        ):
            cap_normal_z = -sign  # cap faces inward

            for i in range(_SEGMENTS):
                j = (i + 1) % _SEGMENTS

                x0, y0 = cone_radius * cos_a[i], cone_radius * sin_a[i]
                x1, y1 = cone_radius * cos_a[j], cone_radius * sin_a[j]

                # Side face
                vertices.extend([
                    [x0, y0, base_z],
                    [x1, y1, base_z],
                    [0,  0,  tip_z],
                ])
                normals.extend([
                    [cos_a[i] * side_r, sin_a[i] * side_r, nz_dir],
                    [cos_a[j] * side_r, sin_a[j] * side_r, nz_dir],
                    [0, 0, nz_dir],
                ])

                # Base cap (wound inward)
                if sign > 0:
                    vertices.extend([
                        [0, 0, base_z], [x1, y1, base_z], [x0, y0, base_z]])
                else:
                    vertices.extend([
                        [0, 0, base_z], [x0, y0, base_z], [x1, y1, base_z]])
                normals.extend([
                    [0, 0, cap_normal_z],
                    [0, 0, cap_normal_z],
                    [0, 0, cap_normal_z],
                ])

        verts = np.array(vertices, dtype=np.float64)
        nrmls = np.array(normals, dtype=np.float64)

        # ---- Rotate to align with the locked axis ----
        if axis == 'x':
            # Rotate +90° around Y: Z-axis → X-axis
            rot = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], dtype=np.float64)
            verts = verts @ rot.T
            nrmls = nrmls @ rot.T
        elif axis == 'y':
            # Rotate -90° around X: Z-axis → Y-axis
            rot = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float64)
            verts = verts @ rot.T
            nrmls = nrmls @ rot.T
        # axis == 'z': already aligned

        # ---- Translate to world position ----
        verts += np.array(
            [float(center_pos.x), float(center_pos.y), float(center_pos.z)],
            dtype=np.float64,
        )

        count = len(verts)
        return verts, nrmls, count
