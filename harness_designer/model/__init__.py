from typing import TYPE_CHECKING

from . import loader as _loader
from ..geometry import point as _point
from ..geometry import angle as _angle

if TYPE_CHECKING:
    from ..database.global_db import model3d as _model3d


class Model:

    def __init__(self, path, db_obj: "_model3d.Model3D"):
        self.vertices, self.faces = _loader.load(path)
        self.db_obj = db_obj

        self._angle = db_obj.angle
        self._o_angle = self._angle.copy()

        self._position = db_obj.offset
        self._o_position = self._position.copy()

    def __update_position(self, position: _point.Point):
        delta = position - self._o_position
        self._o_position = position.copy()

