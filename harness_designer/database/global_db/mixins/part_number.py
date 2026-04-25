from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class PartNumberMixin(BaseMixin):

    @property
    def part_number(self) -> str:
        return self._table.select('part_number', id=self._db_id)[0][0]

    @part_number.setter
    def part_number(self, value: str):
        self._table.update(self._db_id, part_number=value)
        self._populate('part_number')


class PartNumberControl(_prop_grid.StringProperty):

    def __init__(self, parent):
        self.db_obj: PartNumberMixin = None

        super().__init__(parent, 'Part Number')

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_part_number)

    def set_obj(self, db_obj: PartNumberMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue('')
            self.Enable(False)
        else:
            self.SetValue(db_obj.part_number)
            self.Enable(True)

    def _on_part_number(self, evt: _prop_grid.PropertyEvent):
        part_number = evt.GetValue()
        self.db_obj.part_number = part_number
