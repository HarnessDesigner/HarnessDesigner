# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import numpy as np

from ...geometry import point as _point
from ... import check_types as _check_types
from ..canvas_base import camera_base as _camera_base


if TYPE_CHECKING:
    from . import canvas as _canvas


@_check_types.do
def build_lookat_matrix(position: np.ndarray, forward: np.ndarray,
                        up: np.ndarray) -> np.ndarray:
    """
    Row-major (``matrix @ column_vector``) view matrix for a camera at
    *position* looking along *forward*, equivalent to what ``gluLookAt``
    would produce -- built locally here instead of applied via GLU and
    read back from GL. *up* is expected already orthogonal to *forward*
    (as produced by ``CameraBase._calculate_camera()``).

    Lives here (not ``canvas.py``, which calls it as part of its own
    ``_set_view()``) so :meth:`Camera.set` can also call it -- pure
    numpy, no GL state involved despite what normally calls it.
    """

    side = np.cross(forward, up)  # NOQA

    matrix = np.identity(4, dtype=np.float32)
    matrix[0, 0:3] = side
    matrix[1, 0:3] = up
    matrix[2, 0:3] = -forward
    matrix[0, 3] = -np.dot(side, position)
    matrix[1, 3] = -np.dot(up, position)
    matrix[2, 3] = np.dot(forward, position)

    return matrix


class Camera(_camera_base.CameraBase):

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):

        super().__init__(canvas)
        self._position = _point.Point(0.0, self.canvas.config.floor.ground_height + 100.0, 75.0)

    def Reset(self):
        super().Reset()
        self._position.z = 75.0

    @_check_types.do
    def set(self) -> None:
        """Refresh basis vectors (base class), then -- if this camera
        actually moved -- also eagerly rebuild the view/clip/inv_clip
        matrices from the CURRENT position/forward/up, instead of
        waiting for the next real paint frame's own ``_set_view()`` to
        get around to it.

        Needed because :meth:`CameraBase._refresh_active_hover` (every
        movement method's ``_send_event`` calls it, so a keyboard zoom
        with the mouse held still triggers it) runs synchronously right
        after a camera move, well before the next ``_on_draw()`` -- an
        active add-handler's own ``get_position_on_focal_plane``/
        ``UnprojectPoint`` calls from that refresh would otherwise read
        last frame's stale ``focal_distance``/``inv_clip``, computed
        for the position this camera had BEFORE the move that just
        happened. That's genuinely a one-frame-stale bug, not just
        "hasn't repainted yet" -- normal painting still happens on its
        own schedule via ``canvas.update()``; this only front-runs the
        CPU-side matrix math so hover queries answer with this frame's
        real numbers instead of last frame's.

        Reuses the existing ``self._projection``/``self._fov`` --
        those depend only on FOV/aspect/near/far, none of which a
        camera move ever changes -- so only the view matrix actually
        needs rebuilding here. A no-op before the first real
        ``_set_view()`` (``self._projection`` still ``None``), which is
        fine: nothing can be hovering over an add-handler before the
        canvas has ever painted once.
        """
        # CameraBase.set() only recomputes _calculate_camera() output if
        # dirty; it never clears the flag itself (set_view() does), so
        # checking is_dirty AFTER the super() call still reflects
        # whether this camera actually moved since the last set_view().
        super().set()

        if self.is_dirty and self._projection is not None:
            modelview = build_lookat_matrix(
                self.position.as_numpy, self.forward, self.up)
            self.set_view(self._projection, modelview, self._fov)
