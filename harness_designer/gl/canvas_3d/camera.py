# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ...geometry import point as _point
from ... import check_types as _check_types
from ..canvas_base import camera_base as _camera_base


if TYPE_CHECKING:
    from . import canvas as _canvas


class Camera(_camera_base.CameraBase):

    @_check_types.do
    def __init__(self, canvas: "_canvas.Canvas"):

        super().__init__(canvas)
        self._position = _point.Point(0.0, self.canvas.config.floor.ground_height + 100.0, 75.0)

    def Reset(self):
        super().Reset()
        self._position.z = 75.0
