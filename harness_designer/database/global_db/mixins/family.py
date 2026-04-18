from typing import TYPE_CHECKING

import wx

from ....ui.editor_obj import prop_grid as _prop_grid
from .base import BaseMixin


if TYPE_CHECKING:
    from .. import family as _family  # NOQA


class FamilyMixin(BaseMixin):

    @property
    def family(self) -> "_family.Family":
        from .. import family as _family  # NOQA

        family_id = self._table.select('family_id', id=self._db_id)
        return _family.Family(self._table.db.families_table, family_id[0][0])

    @property
    def family_id(self) -> int:
        return self._table.select('family_id', id=self._db_id)[0][0]

    @family_id.setter
    def family_id(self, value: int):
        self._table.update(self._db_id, family_id=value)
        self._populate('family_id')


class FamilyControl(_prop_grid.Category):

    def __init__(self, parent):
        super().__init__(parent, 'Family')

        self.choices: list[str] = []
        self.db_obj: FamilyMixin = None

        self.name_ctrl = _prop_grid.ComboBoxProperty(self, 'Name', '', [])
        self.desc_ctrl = _prop_grid.LongStringProperty(self, 'Description', '')
        self.mfg_ctrl = _prop_grid.StringProperty(self, 'Manufacturer', '', style=wx.TE_READONLY)

        self.name_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_name)
        self.desc_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_desc)

    def set_obj(self, db_obj: FamilyMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.name_ctrl.SetItems([])
            self.name_ctrl.SetValue('')
            self.mfg_ctrl.SetValue('')
            self.desc_ctrl.SetValue('')
            self.name_ctrl.Enable(False)
            self.mfg_ctrl.Enable(False)
            self.desc_ctrl.Enable(False)
        else:
            family = db_obj.family
            mfg_id = family.manufacturer.db_id

            db_obj.table.execute(f'SELECT name FROM families WHERE mfg_id={mfg_id};')

            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(family.name)
            self.mfg_ctrl.SetValue(family.manufacturer.name)
            self.desc_ctrl.SetValue(family.description)
            self.name_ctrl.Enable(True)
            self.mfg_ctrl.Enable(True)
            self.desc_ctrl.Enable(True)

    def _on_name(self, evt: _prop_grid.PropertyEvent):
        name = evt.GetValue()
        mfg_id = self.db_obj.family.mfg_id

        self.db_obj.table.execute(f'SELECT id, description FROM families WHERE name="{name}" AND mfg_id={mfg_id};')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.families_table.insert(name, mfg_id, '')
            db_id = db_obj.db_id
            desc = ''

            self.choices.append(name)
            self.choices.sort()

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(name)

        self.desc_ctrl.SetValue(desc)

        self.db_obj.family_id = db_id

    def _on_desc(self, evt: _prop_grid.PropertyEvent):
        desc = evt.GetValue()
        self.db_obj.family.description = desc
