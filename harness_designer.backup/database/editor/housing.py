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
    from ..global_db import housing as _housing


class HousingsModel(_model_base.ModelBase):
    __table_name__ = 'housings'
    column_mapping = {
        0: 'id',
        1: 'part_number',
        2: 'description',
        3: 'mfg_id',
        4: 'family_id',
        5: 'series_id',
        6: 'color_id',
        7: 'gender_id',
        8: 'direction_id',
        9: 'min_temp_id',
        10: 'max_temp_id',
        11: 'cavity_lock_id',
        12: 'sealing',
        13: 'rows',
        14: 'num_pins',
        15: 'terminal_sizes',
        16: 'centerline',
        17: 'compat_cpas',
        18: 'compat_tpas',
        19: 'compat_covers',
        20: 'compat_terminals',
        21: 'compat_seals',
        22: 'compat_housings',
        23: 'ip_rating_id',
        24: 'length',
        25: 'width',
        26: 'height',
        27: 'weight',
    }
    table: "_housing.HousingsTable" = None

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
            a = self.table.db.genders_table[a].name
            b = self.table.db.genders_table[b].name
        elif col == 8:
            a = self.table.db.directions_table[a].name
            b = self.table.db.directions_table[b].name
        elif col == 9:
            a = self.table.db.temperatures_table[a].name
            b = self.table.db.temperatures_table[b].name
        elif col == 10:
            a = self.table.db.temperatures_table[a].name
            b = self.table.db.temperatures_table[b].name
        elif col == 11:
            a = self.table.db.cavity_locks_table[a].name
            b = self.table.db.cavity_locks_table[b].name
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
            pass
        elif col == 16:
            a = float(a)
            b = float(b)
        elif col == 17:
            pass
        elif col == 18:
            pass
        elif col == 19:
            pass
        elif col == 20:
            pass
        elif col == 21:
            pass
        elif col == 22:
            pass
        elif col == 23:
            a = self.table.db.ip_ratings_table[a].name
            b = self.table.db.ip_ratings_table[b].name
        elif col == 24:
            a = float(a)
            b = float(b)
        elif col == 25:
            a = float(a)
            b = float(b)
        elif col == 26:
            a = float(a)
            b = float(b)
        elif col == 27:
            a = float(a)
            b = float(b)

        if a < b:
            return -1

        if a > b:
            return 1

        return 0

    def AddRow(self, value):
        value = list(value)

        value.insert(9, 0)
        value.insert(10, 0)
        value.insert(11, 0)
        value.insert(27, 0)
        value.insert(28, 0)
        value.append(0)
        value.append(None)

        self.table.insert(*value)
        self.RowAppended()


class HousingsPanel(wx.Panel):
    def __init__(self, parent, table: "_housing.HousingsTable"):
        wx.Panel.__init__(self, parent, -1)

        self.table = table

        # Create a dataview control
        self.dvc = _dataviewctrl.DataViewCtrl(self, style=wx.BORDER_THEME | dv.DV_ROW_LINES | dv.DV_MULTIPLE)

        self.model = HousingsModel(table)
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

        table.execute('SELECT id, name FROM genders ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.GenderRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Gender", renderer, 7)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM directions ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.DirectionRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Direction", renderer, 8)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM temperatures ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.TemperatureRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Temperature (Min)", renderer, 9)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM temperatures ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.TemperatureRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Temperature (Max)", renderer, 10)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM cavity_locks ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.CavityLockRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Cavity Lock", renderer, 11)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Sealing", renderer, 12)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=100, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Rows", renderer, 13)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=255, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Pins", renderer, 14)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _list_choice.TerminalSizeListRenderer(mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Terminal Sizes (mm)", renderer, 15)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=20.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Centerline (mm)", renderer, 16)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _list_choice.CPAListRenderer(table, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Compat CPAs", renderer, 17)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _list_choice.TPAListRenderer(table, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Compat TPAs", renderer, 18)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _list_choice.CoverListRenderer(table, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Compat Covers", renderer, 19)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _list_choice.TerminalListRenderer(table, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Compat Terminals", renderer, 20)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _list_choice.SealListRenderer(table, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Compat Seals", renderer, 21)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _list_choice.HousingListRenderer(table, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Compat Housings", renderer, 22)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        table.execute('SELECT id, name FROM ip_ratings ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.IPRatingRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("IP Rating", renderer, 23)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Length (mm)", renderer, 24)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Width (mm)", renderer, 25)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Height (mm)", renderer, 26)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Weight (g)", renderer, 27)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.dvc, 1, wx.EXPAND)
