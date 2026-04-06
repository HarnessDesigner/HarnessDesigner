from typing import TYPE_CHECKING

from .base import BaseMixin

from wx import propgrid as wxpg


if TYPE_CHECKING:
    from .. import terminal as _terminal


class CompatTerminalsMixin(BaseMixin):

    @property
    def compat_terminals(self) -> list["_terminal.Terminal"]:
        compat_terminals = eval(self._table.select('compat_terminals', id=self._db_id)[0][0])
        res = []
        for part_number in compat_terminals:
            try:
                res.append(self._table.db.terminals_table[part_number])
            except KeyError:
                pass
        return res

    @compat_terminals.setter
    def compat_terminals(self, value: list["_terminal.Terminal"]):
        compat_terminals = [terminal.part_number for terminal in value]
        self._table.update(self._db_id, compat_terminals=str(compat_terminals))

    @property
    def compat_terminals_array(self) -> list[str]:
        return eval(self._table.select('compat_terminals', id=self._db_id)[0][0])

    @compat_terminals_array.setter
    def compat_terminals_array(self, value: list[str]):
        self._table.update(self._db_id, compat_terminals=str(value))

    @property
    def _compat_terminals_propgrid(self) -> wxpg.PGProperty:
        from ....ui.editor_obj.prop_grid import array_string_prop as _array_string_prop

        prop = _array_string_prop.ArrayStringProperty(
            'Compatible Terminals', 'compat_terminals_array', self.compat_terminals_array)

        return prop
