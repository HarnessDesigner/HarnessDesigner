from typing import TYPE_CHECKING

import wx
import wx.dataview as dv

try:
    from .controls import list_choice as _list_choice
    from .controls import choice as _choice
    from .controls import float_spin as _float_spin
    from .controls import model_base as _model_base
    from .controls import dataviewctrl as _dataviewctrl
except ImportError:
    from controls import list_choice as _list_choice
    from controls import choice as _choice
    from controls import float_spin as _float_spin
    from controls import model_base as _model_base
    from controls import dataviewctrl as _dataviewctrl


if TYPE_CHECKING:
    from ..global_db import tpa_lock as _tpa_lock


class TPALocksModel(_model_base.ModelBase):
    __table_name__ = 'tpa_locks'
    column_mapping = {
        0: 'id',
        1: 'part_number',
        2: 'description',
        3: 'mfg_id',
        4: 'family_id',
        5: 'series_id',
        6: 'color_id',
        7: 'min_temp_id',
        8: 'max_temp_id',
        9: 'length',
        10: 'width',
        11: 'height',
        12: 'pins',
        13: 'terminal_size',
        14: 'weight'
    }
    table: "_tpa_lock.TPALocksTable" = None

    def Compare(self, item1, item2, col, ascending):
        if not ascending:
            item2, item1 = item1, item2

        row1 = self.GetRow(item1)
        row2 = self.GetRow(item2)

        a = self.GetValueByRow(row1, col)
        b = self.GetValueByRow(row2, col)

        if col == 0:
            a = int(a)
            b = int(b)
        elif col == 3:
            a = self.table.db.manufacturers_table[a].name
            b = self.table.db.manufacturers_table[b].name
        elif col == 4:
            a = self.table.db.families_table[a].name
            b = self.table.db.families_table[b].name
        elif col == 5:
            a = self.table.db.series_table[a].name
            b = self.table.db.series_table[b].name
        elif col == 6:
            a = self.table.db.colors_table[a].name
            b = self.table.db.colors_table[b].name
        elif col == 7:
            a = self.table.db.temperatures_table[a].name
            b = self.table.db.temperatures_table[b].name
        elif col == 8:
            a = self.table.db.temperatures_table[a].name
            b = self.table.db.temperatures_table[b].name
        elif col == 9:
            a = float(a)
            b = float(b)
        elif col == 10:
            a = float(a)
            b = float(b)
        elif col == 11:
            a = float(a)
            b = float(b)
        elif col == 12:
            pass
        elif col == 13:
            a = float(a)
            b = float(b)
        elif col == 14:
            a = float(a)
            b = float(b)

        if a < b:
            return -1

        if a > b:
            return 1

        return 0

    def AddRow(self, value):
        value = list(value)

        value.insert(7, 0)
        value.insert(8, 0)
        value.insert(9, 0)
        value.append(None)

        self.table.insert(*value)
        self.RowAppended()


class TPALocksPanel(wx.Panel):
    def __init__(self, parent, table: "_tpa_lock.TPALocksTable"):
        wx.Panel.__init__(self, parent, -1)

        self.table = table

        # Create a dataview control
        self.dvc = _dataviewctrl.DataViewCtrl(self, style=wx.BORDER_THEME | dv.DV_ROW_LINES | dv.DV_MULTIPLE)

        self.model = TPALocksModel(table)
        self.dvc.AssociateModel(self.model)

        # Now we create some columns.
        col = self.dvc.AppendTextColumn("DB_ID", 0)
        col.SetAlignment(wx.ALIGN_LEFT)

        col = self.dvc.AppendTextColumn("Part Number", 1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col.SetAlignment(wx.ALIGN_LEFT)

        col = self.dvc.AppendTextColumn("Description", 2, mode=dv.DATAVIEW_CELL_EDITABLE)
        col.SetAlignment(wx.ALIGN_LEFT)

        table.execute('SELECT id, name FROM manufacturers ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.ManufacturerRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Manufacturer", renderer, 3)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM families ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.FamilyRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Family", renderer, 4)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM series ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.SeriesRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Series", renderer, 5)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM colors ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.ColorRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Color", renderer, 6)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM temperatures ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.TemperatureRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Temperature (Min)", renderer, 7)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM temperatures ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.TemperatureRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Temperature (Max)", renderer, 8)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Length (mm)", renderer, 9)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Width (mm)", renderer, 10)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Height (mm)", renderer, 11)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        col = self.dvc.AppendTextColumn("Pins", 12, mode=dv.DATAVIEW_CELL_EDITABLE)
        col.SetAlignment(wx.ALIGN_LEFT)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=20.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Terminal Size (mm)", renderer, 13)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Weight (g)", renderer, 14)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.dvc, 1, wx.EXPAND)
