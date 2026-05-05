from .base import BaseMixin

from ....ui import prop_ctrls as _prop_ctrls


class DescriptionMixin(BaseMixin):

    @property
    def description(self) -> str:
        return self._table.select('description', id=self._db_id)[0][0]

    @description.setter
    def description(self, value: str):
        self._table.update(self._db_id, description=value)
        self._populate('description')


class DescriptionControl(_prop_ctrls.LongStringProperty):

    def __init__(self, parent):
        self.db_obj: DescriptionMixin = None

        super().__init__(parent, 'Description')

        self.Bind(_prop_ctrls.EVT_PROPERTY_CHANGED, self._on_desc)

    def set_obj(self, db_obj: DescriptionMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue('')
            self.Enable(False)
        else:
            self.SetValue(db_obj.description)
            self.Enable(True)

    def _on_desc(self, evt: _prop_ctrls.PropertyEvent):
        desc = evt.GetValue()
        self.db_obj.description = desc
