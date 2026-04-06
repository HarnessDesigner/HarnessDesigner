import uuid
from wx import propgrid as wxpg

from .base import BaseMixin
from ....geometry import point as _point


class DimensionMixin(BaseMixin):
    _scale_id: str = None

    def _update_scale(self, scale: _point.Point):
        width, height, length = scale.as_float

        self._table.update(self._db_id, width=width, height=height, length=length)

    @property
    def scale(self) -> "_point.Point":
        if self._scale_id is None:
            self._scale_id = str(uuid.uuid4())

        x = self.width
        y = self.height
        z = self.length

        if x <= 0:
            self._table.update(self._db_id, width=1.0)
            x = 1.0

        if y <= 0:
            self._table.update(self._db_id, height=1.0)
            y = 1.0

        if z <= 0:
            self._table.update(self._db_id, length=1.0)
            z = 1.0

        scale = _point.Point(x, y, z, db_id=self._scale_id)
        scale.bind(self._update_scale)
        return scale

    @property
    def length(self) -> float:
        return self._table.select('length', id=self._db_id)[0][0]

    @length.setter
    def length(self, value: float):
        self._table.update(self._db_id, length=value)

    @property
    def width(self) -> float:
        return self._table.select('width', id=self._db_id)[0][0]

    @width.setter
    def width(self, value: float):
        self._table.update(self._db_id, width=value)

    @property
    def height(self) -> float:
        return self._table.select('height', id=self._db_id)[0][0]

    @height.setter
    def height(self, value: float):
        self._table.update(self._db_id, height=value)

    @property
    def _dimension_propgrid(self) -> wxpg.PGProperty:
        from ....ui.editor_obj.prop_grid import float_prop as _float_prop

        group_prop = wxpg.PGProperty('Dimensions', '')

        length_prop = _float_prop.FloatProperty('Length', 'length', self.length, min_value=0.01, max_value=999.0, increment=0.01, units='mm')
        width_prop = _float_prop.FloatProperty('Width', 'width', self.width, min_value=0.01, max_value=999.0, increment=0.01, units='mm')
        height_prop = _float_prop.FloatProperty('Height', 'height', self.height, min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        group_prop.AppendChild(length_prop)
        group_prop.AppendChild(width_prop)
        group_prop.AppendChild(height_prop)

        return group_prop
