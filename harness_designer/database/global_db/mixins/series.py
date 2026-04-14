from typing import TYPE_CHECKING

import wx
from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import series as _series  # NOQA


class SeriesMixin(BaseMixin):

    @property
    def series(self) -> "_series.Series":
        from .. import series as _series  # NOQA

        series_id = self._table.select('series_id', id=self._db_id)
        return _series.Series(self._table.db.series_table, series_id[0][0])

    @series.setter
    def series(self, value: "_series.Series"):
        self._table.update(self._db_id, series_id=value.db_id)

    @property
    def series_id(self) -> int:
        return self._table.select('series_id', id=self._db_id)[0][0]

    @series_id.setter
    def series_id(self, value: int):
        self._table.update(self._db_id, series_id=value)


class SeriesControl(_prop_grid.Category):

    def __init__(self, parent):
        super().__init__(parent, 'Series')

        self.choices: list[str] = []
        self.db_obj: SeriesMixin = None

        self.name_ctrl = _prop_grid.ComboBoxProperty(self, 'Name', '', [])
        self.desc_ctrl = _prop_grid.LongStringProperty(self, 'Description', '')
        self.mfg_ctrl = _prop_grid.StringProperty(self, 'Manufacturer', '', style=wx.TE_READONLY)

        self.name_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_name)
        self.desc_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_desc)

    def set_obj(self, db_obj: SeriesMixin):

        series = db_obj.series
        mfg_id = series.manufacturer.db_id

        db_obj.table.execute(f'SELECT name FROM series WHERE mfg_id={mfg_id};')

        rows = db_obj.table.fetchall()

        choices = sorted([row[0] for row in rows])

        self.name_ctrl.SetItems(choices)
        self.name_ctrl.SetValue(series.name)
        self.mfg_ctrl.SetValue(series.manufacturer.name)
        self.desc_ctrl.SetValue(series.description)

    def _on_name(self, evt: _prop_grid.PropertyEvent):
        name = evt.GetValue()
        mfg_id = self.db_obj.series.mfg_id

        self.db_obj.table.execute(f'SELECT id, description FROM series WHERE name="{name}" AND mfg_id={mfg_id};')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.series_table.insert(name, mfg_id, '')
            db_id = db_obj.db_id
            desc = ''

            self.choices.append(name)
            self.choices.sort()

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(name)

        self.desc_ctrl.SetValue(desc)

        self.db_obj.series_id = db_id

    def _on_desc(self, evt: _prop_grid.PropertyEvent):
        desc = evt.GetValue()
        self.db_obj.series.description = desc
