from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import plating as _plating


class PlatingMixin(BaseMixin):

    @property
    def plating(self) -> "_plating.Plating":
        plating_id = self.plating_id
        return self._table.db.platings_table[plating_id]

    @property
    def plating_id(self) -> int:
        return self._table.select('plating_id', id=self._db_id)[0][0]

    @plating_id.setter
    def plating_id(self, value: int):
        self._table.update(self._db_id, plating_id=value)
        self._populate('plating_id')


class PlatingControl(_prop_grid.Category):

    def __init__(self, parent):
        super().__init__(parent, 'Plating')

        self.attribute_name = 'plating'

        self.choices: list[str] = []
        self.db_obj: PlatingMixin = None

        self.symbol_ctrl = _prop_grid.ComboBoxProperty(self, 'Symbol')
        self.desc_ctrl = _prop_grid.LongStringProperty(self, 'Description')

        self.symbol_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_symbol)
        self.desc_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_desc)

    def set_obj(self, db_obj: PlatingMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.symbol_ctrl.SetItems(self.choices)
            self.symbol_ctrl.SetValue('')
            self.desc_ctrl.SetValue('')

            self.symbol_ctrl.Enable(False)
            self.desc_ctrl.Enable(False)
        else:
            plating = getattr(db_obj, self.attribute_name)

            db_obj.table.execute(f'SELECT symbol FROM platings;')

            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])

            self.symbol_ctrl.SetItems(self.choices)
            self.symbol_ctrl.SetValue(plating.symbol)
            self.desc_ctrl.SetValue(plating.description)

            self.symbol_ctrl.Enable(True)
            self.desc_ctrl.Enable(True)

    def _on_symbol(self, evt: _prop_grid.PropertyEvent):
        symbol = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id, description FROM platings WHERE symbol="{symbol}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.platings_table.insert(symbol, '')
            db_id = db_obj.db_id
            desc = ''

            self.choices.append(symbol)
            self.choices.sort()

            self.symbol_ctrl.SetItems(self.choices)
            self.symbol_ctrl.SetValue(symbol)

        self.desc_ctrl.SetValue(desc)

        setattr(self.db_obj, self.attribute_name + '_id', db_id)

    def SetAttributeName(self, name):
        self.attribute_name = name

    def _on_desc(self, evt: _prop_grid.PropertyEvent):
        desc = evt.GetValue()
        getattr(self.db_obj, self.attribute_name).description = desc
