from typing import TYPE_CHECKING

import wx

from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin

if TYPE_CHECKING:
    from .. import protection as _protection


class ProtectionMixin(BaseMixin):

    @property
    def protection_id(self) -> int:
        return self._table.select('protection_id', id=self._db_id)[0][0]

    @protection_id.setter
    def protection_id(self, value: int):
        self._table.update(self._db_id, protection_id=value)

    @property
    def protections(self) -> "_protection.Protection":
        protection_id = self.protection_id
        return self.table.db.protections_table[protection_id]


class ProtectionControl(_prop_grid.AutocompleteStringProperty):

    def __init__(self, parent):
        self.db_obj: ProtectionMixin = None
        self.choices: list[str] = []

        super().__init__(parent, 'Protections', '', choices=[])

        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_protection)

    def set_obj(self, db_obj: ProtectionMixin):
        self.db_obj = db_obj

        db_obj.table.execute('SELECT name FROM protections;')
        rows = db_obj.table.fetchall()

        self.choices = [row[0] for row in rows]

        self.SetItems(self.choices)
        self.SetValue(db_obj.protections.name)

    def _on_protection(self, evt: _prop_grid.PropertyEvent):
        protection = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM protections WHERE name="{protection}";')
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.protections_table.insert(protection)
            db_id = db_obj.db_id

            self.choices.append(protection)
            self.SetItems(self.choices)
            self.SetValue(protection)

        self.db_obj.protection_id = db_id
