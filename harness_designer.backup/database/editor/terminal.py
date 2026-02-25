
from typing import TYPE_CHECKING

import wx
import wx.dataview as dv


try:
    from .controls import list_choice as _list_choice
    from .controls import choice as _choice
    from .controls import float_spin as _float_spin
    from .controls import int_spin as _int_spin
    from .controls import model_base as _model_base
    from .controls import dataviewctrl as _dataviewctrl
except ImportError:
    from controls import list_choice as _list_choice
    from controls import choice as _choice
    from controls import float_spin as _float_spin
    from controls import int_spin as _int_spin
    from controls import model_base as _model_base
    from controls import dataviewctrl as _dataviewctrl


if TYPE_CHECKING:
    from ..global_db import terminal as _terminal


class TerminalsModel(_model_base.ModelBase):
    __table_name__ = 'terminals'
    column_mapping = {
        0: 'id',
        1: 'part_number',
        2: 'description',
        3: 'mfg_id',
        4: 'family_id',
        5: 'series_id',
        6: 'plating_id',
        7: 'gender_id',
        8: 'sealing',
        9: 'cavity_lock_id',
        10: 'blade_size',
        11: 'resistance_mohms',
        12: 'mating_cycles',
        13: 'max_vibration_g',
        14: 'max_current_ma',
        15: 'wire_size_min_awg',
        16: 'wire_size_max_awg',
        17: 'wire_dia_min',
        18: 'wire_dia_max',
        19: 'min_wire_cross',
        20: 'max_wire_cross',
        21: 'length',
        22: 'width',
        23: 'height',
        24: 'weight'
    }
    table: "_terminal.TerminalsTable" = None

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
            a = self.table.db.platings_table[a].description
            b = self.table.db.platings_table[b].description
        elif col == 7:
            a = self.table.db.genders_table[a].name
            b = self.table.db.genders_table[b].name
        elif col == 8:
            a = int(a)
            b = int(b)
        elif col == 9:
            a = self.table.db.cavity_locks_table[a].name
            b = self.table.db.cavity_locks_table[b].name
        elif col == 10:
            a = float(a)
            b = float(b)
        elif col == 11:
            a = float(a)
            b = float(b)
        elif col == 12:
            a = int(a)
            b = int(b)
        elif col == 13:
            a = int(a)
            b = int(b)
        elif col == 14:
            a = int(a)
            b = int(b)
        elif col == 15:
            a = int(a)
            b = int(b)
        elif col == 16:
            a = int(a)
            b = int(b)
        elif col == 17:
            a = float(a)
            b = float(b)
        elif col == 18:
            a = float(a)
            b = float(b)
        elif col == 19:
            a = float(a)
            b = float(b)
        elif col == 20:
            a = float(a)
            b = float(b)
        elif col == 21:
            a = float(a)
            b = float(b)
        elif col == 22:
            a = float(a)
            b = float(b)
        elif col == 23:
            a = float(a)
            b = float(b)
        elif col == 24:
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


class TerminalsPanel(wx.Panel):
    def __init__(self, parent, table: "_terminal.TerminalsTable"):
        wx.Panel.__init__(self, parent, -1)

        self.table = table

        # Create a dataview control
        self.dvc = _dataviewctrl.DataViewCtrl(self, style=wx.BORDER_THEME | dv.DV_ROW_LINES | dv.DV_MULTIPLE)

        self.model = TerminalsModel(table)
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

        table.execute('SELECT id, description FROM platings ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.ColorRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Plating", renderer, 6)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM genders ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.GenderRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Gender", renderer, 7)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Sealing", renderer, 8)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM cavity_locks ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.CavityLockRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Cavity Lock", renderer, 9)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=20.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Blade Size (mm)", renderer, 10)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Resistance (mOhms)", renderer, 11)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=9999, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Mating Cycles", renderer, 12)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=255, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Max Vibration (g)", renderer, 13)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=9999999, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Max Current (ma)", renderer, 14)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=30, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Wire Size (Min, AWG)", renderer, 15)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=30, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Wire Size (Max, AWG)", renderer, 16)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=99.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Wire Diameter (Min, mm)", renderer, 17)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=99.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Wire Diameter (Max, mm)", renderer, 18)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Wire Size (Min, mm2)", renderer, 19)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Wire Size (Max, mm2)", renderer, 20)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Length (mm)", renderer, 21)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Width (mm)", renderer, 22)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Height (mm)", renderer, 23)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Weight (g)", renderer, 24)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.dvc, 1, wx.EXPAND)
