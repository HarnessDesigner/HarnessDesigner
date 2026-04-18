from typing import TYPE_CHECKING

from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


if TYPE_CHECKING:
    from .. import terminal as _terminal


class CompatTerminalsMixin(BaseMixin):

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        compat_terminals = self.compat_terminals_array
        res = []
        for part_number in compat_terminals:
            try:
                res.append(self._table.db.terminals_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_terminals_array(self) -> list[str]:
        value = self._table.select('compat_terminals', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_terminals_array.setter
    def compat_terminals_array(self, value: list[str]):
        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, compat_terminals=value)
        self._populate('compat_terminals_array')


class CompatTerminalsControl(_prop_grid.ArrayStringProperty):

    def __init__(self, parent):
        self.db_obj: CompatTerminalsMixin = None
        super().__init__(parent, 'Compatible Terminals', [])

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_compat_housings)

    def set_obj(self, db_obj: CompatTerminalsMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue([])
            self.Enable(False)
        else:
            self.SetValue(db_obj.compat_terminals_array)
            self.Enable(True)

    def _on_compat_housings(self, evt: _prop_grid.PropertyEvent):
        compat_terminals = evt.GetValue()
        self.db_obj.compat_terminals_array = compat_terminals