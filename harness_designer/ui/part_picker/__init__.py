
from typing import TYPE_CHECKING

import wx
import wx.lib.mixins.listctrl as listmix

from . import model_preview as _model_preview

if TYPE_CHECKING:
    from ...database.global_db import TableBase


class ListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):

    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)


class PartPickerPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_NONE, style=wx.BORDER_SUNKEN)
        self.db_table: "TableBase" = None
        self.selected_item = None

        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        self.list_ctrl = ListCtrl(self, wx.ID_ANY, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
        hsizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.preview = _model_preview.Preview3D(self)
        hsizer.Add(self.preview, 1)
        vsizer.Add(hsizer, 1)

        self.SetSizer(vsizer)
        self.SetMinSize((150, 300))

        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selected)

    def on_selected(self, evt: wx.ListEvent):
        item = self.list_ctrl.GetFirstSelected()
        db_id = self.list_ctrl.GetItemData(item)
        self.selected_item = self.db_table[db_id]
        evt.Skip()

    def add_items(self, db_table: "TableBase"):
        self.list_ctrl.ClearAll()

        data, _ = db_table.parts_list()

        for column, label in enumerate(db_table.headers):
            self.list_ctrl.AppendColumn(label, format=wx.LIST_FORMAT_CENTER)
            self.list_ctrl.SetColumnWidth(column, wx.LIST_AUTOSIZE)

        for index, (part_number, params) in enumerate(list(data.items())):
            params = (part_number,) + params

            for column, label in enumerate(params[:-1]):
                self.list_ctrl.SetItem(self, index, column, str(label))

            self.list_ctrl.SetItemData(index, params[-1])

        self.db_table = db_table
