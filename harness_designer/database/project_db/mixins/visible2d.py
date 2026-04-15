
from ....ui.editor_obj import prop_grid as _prop_grid
from .base import BaseMixin


class Visible2DMixin(BaseMixin):

    @property
    def is_visible2d(self) -> bool:
        return bool(self._table.select('is_visible2d', id=self._db_id)[0][0])

    @is_visible2d.setter
    def is_visible2d(self, value: bool):
        self._table.update(self._db_id, is_visible2d=int(value))


class Visible2DControl(_prop_grid.BoolProperty):

    def __init__(self, parent):
        self.db_obj: Visible2DMixin = None

        super().__init__(parent, 'Is Visible 2D', False)

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_visible2d)

    def _on_visible2d(self, evt):
        value = evt.GetValue()
        self.db_obj.is_visible2d = value

    def set_obj(self, db_obj: Visible2DMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue(False)
            self.Enable(False)
        else:
            self.SetValue(db_obj.is_visible2d)
            self.Enable(True)
