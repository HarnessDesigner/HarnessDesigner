import uuid
from ....ui.editor_obj import prop_grid as _prop_grid

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
        self._populate('length')

    @property
    def width(self) -> float:
        return self._table.select('width', id=self._db_id)[0][0]

    @width.setter
    def width(self, value: float):
        self._table.update(self._db_id, width=value)
        self._populate('width')

    @property
    def height(self) -> float:
        return self._table.select('height', id=self._db_id)[0][0]

    @height.setter
    def height(self, value: float):
        self._table.update(self._db_id, height=value)
        self._populate('height')


class DimensionControl(_prop_grid.Category):

    def __init__(self, parent):
        self.db_obj: DimensionMixin = None

        super().__init__(parent, 'Dimensions')

        self.length_ctrl = _prop_grid.FloatProperty(
            self, 'Length', min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        self.width_ctrl = _prop_grid.FloatProperty(
            self, 'Width', min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        self.height_ctrl = _prop_grid.FloatProperty(
            self, 'Height', min_value=0.01, max_value=999.0, increment=0.01, units='mm')

        self.length_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_length)
        self.width_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_width)
        self.height_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_height)

    def set_obj(self, db_obj: DimensionMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.length_ctrl.SetValue(0.0)
            self.width_ctrl.SetValue(0.0)
            self.height_ctrl.SetValue(0.0)
            self.length_ctrl.Enable(False)
            self.width_ctrl.Enable(False)
            self.height_ctrl.Enable(False)
        else:
            self.length_ctrl.SetValue(db_obj.length)
            self.width_ctrl.SetValue(db_obj.width)
            self.height_ctrl.SetValue(db_obj.height)
            self.length_ctrl.Enable(True)
            self.width_ctrl.Enable(True)
            self.height_ctrl.Enable(True)

    def _on_length(self, evt: _prop_grid.PropertyEvent):
        self.db_obj.length = evt.GetValue()

    def _on_width(self, evt: _prop_grid.PropertyEvent):
        self.db_obj.width = evt.GetValue()

    def _on_height(self, evt: _prop_grid.PropertyEvent):
        self.db_obj.height = evt.GetValue()
