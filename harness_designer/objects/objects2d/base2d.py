# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import math

import numpy as np
from OpenGL import GL

from .. import objectsvar as _objectsvar

from ...geometry import point as _point
from ...geometry import angle as _angle
from ...geometry.angle import quaternion as _quaternion
from ... import color as _color
from ... import config as _config
from ...gl import materials as _materials
from ...gl import vbo as _vbo
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import ObjectBase as _ObjectBase
    from ... import ui as _ui
    from ...ui import editor_2d as _editor_2d
    from ...database import project_db as _project_db
    from ...gl import vbo as _vbo


Config = _config.Config.editor2d


@_check_types.do
def _quat_about_y(degrees: float) -> _quaternion.Quaternion:
    """Return the quaternion rotating *degrees* about world Y.

    Not used by ``Base2D`` itself -- ``_render_geometry``/``BaseVar``'s
    ``_compute_obb``/``_compute_aabb`` all use ``self._angle``'s own
    native quaternion directly (``angle2d.y``, since that's the axis a
    Y=0-flat 2D primitive must spin about to stay flat -- see
    ``objects2d/housing_layout.py``, the source that writes it). Kept as
    a plain utility for callers that need a raw Y-rotation quaternion/
    point-rotation without going through a live ``Angle`` object at all
    (e.g. ``objects2d/housing.py``'s extras positioning).
    """
    return _quaternion.Quaternion.from_axis_angle([0.0, 1.0, 0.0], math.radians(degrees))


@_check_types.do
def _rotate_about_y(points: np.ndarray, degrees: float) -> np.ndarray:
    """Rotate an ``(N, 3)`` array of points about world Y by *degrees*.

    Same quaternion-vector rotation formula already used throughout the
    project_db angle-update paths (e.g. ``PJTHousing._update_angle3d``).
    """
    q = _quat_about_y(degrees)
    qvec = np.array([q.x, q.y, q.z], dtype=np.float32)
    t = np.cross(qvec, points)
    return points + 2.0 * q.w * t + 2.0 * np.cross(qvec, t)


class Base2D(_objectsvar.BaseVar):
    """
    Base class for 2D schematic representations of objects

    Uses OpenGL for rendering in the 2D schematic editor. Objects that
    render via a shared primitive VBO (see ``shapes/``) pass ``vbo``/
    ``scale``/``material`` and get the same lifecycle
    ``objects.objects3d.base3d.Base3D`` uses (``_compute_obb``/
    ``_compute_aabb``, bound position/angle/scale updates, selection
    material swap, ``_render_geometry``) -- see ``objects2d/housing.py``
    for the first (and so far only) real user of this path. Object types
    not yet migrated from the legacy immediate-mode ``render_gl()`` path
    (terminal, cavity, wire, ...) simply don't pass them and keep working
    unchanged (``vbo`` stays ``None``).
    """

    @_check_types.do
    def __init__(self, parent: "_ObjectBase", db_obj: "_project_db.PJTEntryBase",
                 vbo: _vbo.PooledVBOHandler, angle: _angle.Angle,
                 position: _point.Point, scale: _point.Point,
                 material: _materials.GLMaterial):
        """Initialise the :class:`Base2D` instance.

        :param parent: Parent object.
        :type parent: _ObjectBase
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_project_db.PJTEntryBase`
        :param position: Position value (``position2d``).
        :type position: :class:`_point.Point`
        :param angle: Value for ``angle`` (``angle2d``; only ``.z`` is
            meaningful -- this app's single-DOF 2D rotation convention).
        :type angle: :class:`_angle.Angle`
        :param vbo: Shared primitive VBO to render with. ``None`` (default)
            for object types still on the legacy immediate-mode path.
        :type vbo: :class:`_vbo.PooledVBOHandler` | None
        :param scale: World-space size to render the unit-sized ``vbo`` at.
        :type scale: :class:`_point.Point` | None
        :param material: Fill material/colour.
        :type material: :class:`_materials.GLMaterial` | None
        """

        try:
            self.editor2d: "_editor_2d.Editor2D" = parent.mainframe.editor2d
            self.mainframe: "_ui.MainFrame" = parent.mainframe
        except AttributeError:
            return

        super().__init__(parent, db_obj, vbo, angle, position, scale, material)

        try:
            self._is_visible = db_obj.is_visible3d  # NOQA
            self.db_obj.bind(self._is_visible_callback, 'is_visible3d')
        except AttributeError:
            self._is_visible = False

        if vbo is None:
            # Legacy immediate-mode contract -- unchanged for object types
            # not yet migrated to the VBO/shader pipeline.
            self._scale = None
            self._material = None
            self._unselected_material = None
            self._selected_material = None
            self._obb = None
            self._aabb = None
        else:
            self._compute_obb()
            self._compute_aabb()

    @property
    @_check_types.do
    def editor(self):
        return self.editor2d

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
            self.db_obj.is_visible2d = value
        except AttributeError:
            pass

    @property
    @_check_types.do
    def _selected_color(self) -> _color.Color:
        return _color.Color(*Config.colors.selected)

    @_check_types.do
    def _is_visible_callback(self, *_, **__):
        self._is_visible = self.db_obj.is_visible2d  # NOQA
        self.mainframe.editor2d.Refresh()

    @_check_types.do
    def _render_geometry(self, program, pos_loc, rot_loc, scale_loc, normal_loc=None):
        """Render this object's VBO using the already-bound *program*.

        Mirrors ``Base3D._render_geometry`` exactly -- ``self._angle``'s
        own native quaternion is used directly, no reinterpretation here.
        The angle's *source* (whatever sets ``angle2d``, e.g.
        ``objects2d/housing_layout.py``) is responsible for writing a
        rotation that's actually correct for a Y=0-flat 2D primitive
        (about world Y) -- see ``angle2d.y``, not ``.z``.
        """
        if self._vbo is None:
            return

        if normal_loc is not None:
            GL.glUniform1i(normal_loc, int(getattr(self, 'smooth', False)))

        GL.glUniform3f(pos_loc, self._position.x, 0.0, self._position.z)
        GL.glUniform4f(rot_loc, *[float(str(v)) for v in self._angle.as_quat_numpy.tolist()])
        GL.glUniform3f(scale_loc, *self._scale.as_float)

        self._vbo.render()

    # ------------------------------------------------------------------
    # Hit-testing / bounds -- subclasses (Housing2D et al.) override these
    # against the OBB/AABB computed above; legacy subclasses override them
    # against their own manual geometry as before.
    # ------------------------------------------------------------------

    @_check_types.do
    def render_gl(self) -> None:
        """
        Legacy immediate-mode render hook -- unused by VBO-backed objects
        (rendered instead by ``gl.canvas2d.canvas.Canvas.paintGL``'s VBO
        pass). Override in legacy subclasses.
        """
        pass

    @_check_types.do
    def render_selection(self, program: int, proj, view) -> None:
        """
        Render selection highlight using the schematic2d shader.

        Override this method to customise selection appearance.
        """
        pass

    @_check_types.do
    def hit_test(self, world_pos: _point.Point) -> bool:
        """
        Test if a point hits this object

        Args:
            world_pos: world position

        Returns:
            True if the point hits this object
        """
        return False

    @_check_types.do
    def get_bounds(self):
        """
        Get the world-space bounding box from the OBB/AABB ``BaseVar``
        already computes for any VBO-backed object -- generic for every
        such subclass (Housing2D, Cavity2D, Terminal2D, ...); legacy
        (``vbo is None``) subclasses have no ``_aabb`` and fall through
        to ``None``.

        Returns:
            tuple: (min_x, min_z, max_x, max_z) or None
        """
        if self._aabb is None:
            return None

        (min_x, _, min_z), (max_x, _, max_z) = self._aabb
        return float(min_x), float(min_z), float(max_x), float(max_z)

    @_check_types.do
    def move_to(self, world_x: float, world_y: float):
        """
        Move this object to a new position

        Args:
            world_x: New world X coordinate
            world_y: New world Y coordinate
        """
        pass
