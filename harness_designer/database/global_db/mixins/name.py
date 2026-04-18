from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class NameMixin(BaseMixin):

    @property
    def name(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @name.setter
    def name(self, value: str):
        self._table.update(self._db_id, name=value)
        self._populate('name')


class NameControl(_prop_grid.StringProperty):

    def set_obj(self, db_obj: NameMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue('')
            self.Enable(False)
        else:
            self.SetValue(db_obj.name)
            self.Enable(True)

    def _on_name(self, evt):
        value = evt.GetValue()
        self.db_obj.name = value

    def __init__(self, parent):
        self.db_obj: NameMixin = None
        super().__init__(parent, 'Name', '')

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_name)

