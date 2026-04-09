from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin
from ....geometry import point as _point
from .. import pjt_point3d as _pjt_point3d


class Position3DMixin(BaseMixin):

    _stored_position3d: _pjt_point3d.PJTPoint3D = None

    @property
    def position3d(self) -> _point.Point:
        if self._stored_position3d is None and self._obj is not None:
            point_id = self.position3d_id

            self._stored_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_position3d.add_object(self._obj)
            point = self._stored_position3d.point
        elif self._stored_position3d is not None:
            point = self._stored_position3d.point
        else:
            point = None

        return point

    @property
    def position3d_id(self) -> int:
        point_id = self._table.select('point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                                (self._table.project_id, 0.0, 0.0, 0.0))

            self._table.commit()
            point_id = self._table.lastrowid
            self.position3d_id = point_id

        return point_id

    @position3d_id.setter
    def position3d_id(self, value: int):
        self._table.update(self._db_id, point3d_id=value)
        
    @property
    def _position3d_propgrid(self) -> _prop_grid.Property:
        _ = self.position3d

        position_prop = self._stored_position3d.propgrid
        return position_prop
