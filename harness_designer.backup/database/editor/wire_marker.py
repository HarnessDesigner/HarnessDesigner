from typing import TYPE_CHECKING

import wx
import wx.dataview as dv

try:
    from .controls import choice as _choice
    from .controls import float_spin as _float_spin
    from .controls import int_spin as _int_spin
    from .controls import model_base as _model_base
    from .controls import dataviewctrl as _dataviewctrl
except ImportError:
    from controls import choice as _choice
    from controls import float_spin as _float_spin
    from controls import int_spin as _int_spin
    from controls import model_base as _model_base
    from controls import dataviewctrl as _dataviewctrl


if TYPE_CHECKING:
    from ..global_db import wire_marker as _wire_marker


class WireMarkersModel(_model_base.ModelBase):
    __table_name__ = 'wire_markers'
    column_mapping = {
        0: 'id',
        1: 'part_number',
        2: 'description',
        3: 'mfg_id',
        4: 'color_id',
        5: 'min_diameter',
        6: 'max_diameter',
        7: 'min_awg',
        8: 'max_awg',
        9: 'length',
        10: 'weight',
        11: 'has_label'
    }
    table: "_wire_marker.WireMarkersTable" = None

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
            a = self.table.db.colors_table[a].name
            b = self.table.db.colors_table[b].name
        elif col == 5:
            a = float(a)
            b = float(b)
        elif col == 6:
            a = float(a)
            b = float(b)
        elif col == 7:
            a = int(a)
            b = int(b)
        elif col == 8:
            a = int(a)
            b = int(b)
        elif col == 9:
            a = float(a)
            b = float(b)
        elif col == 10:
            a = float(a)
            b = float(b)
        elif col == 11:
            a = int(a)
            b = int(b)

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

        self.table.insert(*value)
        self.RowAppended()


class WireMarkerPanel(wx.Panel):
    def __init__(self, parent, table: "_wire_marker.WireMarkersTable"):
        wx.Panel.__init__(self, parent, -1)

        self.table = table

        # Create a dataview control
        self.dvc = _dataviewctrl.DataViewCtrl(self, style=wx.BORDER_THEME | dv.DV_ROW_LINES | dv.DV_MULTIPLE)

        self.model = WireMarkersModel(table)
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

        table.execute('SELECT id, name FROM colors ORDER BY id ASC;')
        choices = table.fetchall()
        renderer = _choice.ColorRenderer(choices, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Color", renderer, 4)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Diameter (Min, mm)", renderer, 5)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.01, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Diameter (Max, mm)", renderer, 6)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=30, allow_none=True, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Size (Min, AWG)", renderer, 7)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=30, allow_none=True, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Size (Max, AWG)", renderer, 8)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Length (mm)", renderer, 9)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _float_spin.FloatSpinRenderer(min_val=0.0, max_val=999.0, increment=0.1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Weight (g)", renderer, 10)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        renderer = _int_spin.IntSpinRenderer(min_val=0, max_val=1, mode=dv.DATAVIEW_CELL_EDITABLE)
        col = _dataviewctrl.DataViewColumn("Has Label", renderer, 11)
        col.SetAlignment(wx.ALIGN_LEFT)
        self.dvc.AppendColumn(col)

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.dvc, 1, wx.EXPAND)
