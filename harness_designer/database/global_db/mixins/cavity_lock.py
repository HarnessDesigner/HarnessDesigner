from typing import TYPE_CHECKING

import wx
from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import cavity_lock as _cavity_lock  # NOQA


class CavityLockMixin(BaseMixin):

    @property
    def cavity_lock(self) -> "_cavity_lock.CavityLock":
        from ..cavity_lock import CavityLock
        lock_id = self.cavity_lock_id

        return CavityLock(self._table.db.cavity_locks_table, lock_id)

    @cavity_lock.setter
    def cavity_lock(self, value: "_cavity_lock.CavityLock"):
        self._table.update(self._db_id, cavity_lock_id=value.db_id)

    @property
    def cavity_lock_id(self) -> int:
        return self._table.select('cavity_lock_id', id=self._db_id)[0][0]

    @cavity_lock_id.setter
    def cavity_lock_id(self, value: int):
        self._table.update(self._db_id, cavity_lock_id=value)


class CavityLockControl(_prop_grid.Property):

    def __init__(self, parent):
        super().__init__(parent, 'Cavity Lock', orientation=wx.VERTICAL)
        self.db_obj: CavityLockMixin = None
        self.choices: list[str] = []

        self.name_ctrl = _prop_grid.ComboBoxProperty(self, 'Name', '', choices=[])
        self.desc_ctrl = _prop_grid.StringProperty(self, 'Description', '')
        self.name_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_name)
        self.desc_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_desc)

    def set_obj(self, db_obj: CavityLockMixin):
        self.db_obj = db_obj

        cavity_lock = db_obj.cavity_lock
        db_obj.table.execute(f'SELECT name FROM cavity_locks;')

        rows = db_obj.table.fetchall()

        choices = sorted([row[0] for row in rows])
        self.name_ctrl.SetItems(choices)
        self.name_ctrl.SetValue(cavity_lock.name)

    def _on_name(self, evt: _prop_grid.PropertyEvent):
        name = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id, description FROM cavity_locks WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.cavity_locks_table.insert(name, '')
            db_id = db_obj.db_id
            desc = ''

            self.choices.append(name)
            self.choices.sort()

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(name)

        self.db_obj.cavity_lock_id = db_id
        self.desc_ctrl.SetValue(desc)

    def _on_desc(self, evt: _prop_grid.PropertyEvent):
        desc = evt.GetValue()
        self.db_obj.cavity_lock.description = desc
