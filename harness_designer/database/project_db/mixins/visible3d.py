from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin


class Visible3DMixin(BaseMixin):

    @property
    def is_visible3d(self) -> bool:
        return bool(self._table.select('is_visible3d', id=self._db_id)[0][0])

    @is_visible3d.setter
    def is_visible3d(self, value: bool):
        self._table.update(self._db_id, is_visible3d=int(value))
        self._populate('is_visible3d')


class Visible3DControl(_prop_grid.BoolProperty):

    def __init__(self, parent):
        self.db_obj: Visible3DMixin = None

        super().__init__(parent, 'Is Visible 3D')

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_visible3d)

    def _on_visible3d(self, evt):
        value = evt.GetValue()
        self.db_obj.is_visible3d = value

    def set_obj(self, db_obj: Visible3DMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue(False)
            self.Enable(False)
        else:
            self.SetValue(db_obj.is_visible3d)
            self.Enable(True)
