import wx
from wx.lib import popupctl as _popupctrl

from ... import utils
from ...database import global_db as _global_db
from ...database.global_db import accessory as _accessory
from . import part_numberctrl as _part_numberctrl
from . import descriptionctrl as _descriptionctrl
from . import familyctrl as _familyctrl
from . import seriesctrl as _seriesctrl
from . import colorctrl as _colorctrl
from . import materialctrl as _materialctrl
from . import manufacturerctrl as _manufacturerctrl


class CheckListCtrl(wx.ListCtrl):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, wx.ID_ANY, pos=(0, 0), style=wx.LC_REPORT)

        self.EnableCheckBoxes()

    def SetItems(self, items: list[tuple[_accessory.Accessory, bool]]):
        self.ClearAll()
        self.AppendColumn('Part Number', wx.LIST_FORMAT_CENTER)
        self.AppendColumn('Manufacturer', wx.LIST_FORMAT_CENTER)
        self.AppendColumn('Description', wx.LIST_FORMAT_CENTER)
        self.AppendColumn('Family', wx.LIST_FORMAT_CENTER)
        self.AppendColumn('Series', wx.LIST_FORMAT_CENTER)

        for db_obj, is_checked in items:
            index = self.InsertItem(self.GetItemCount(), db_obj.part_number)
            self.SetItem(index, 1, db_obj.manufacturer.name)
            self.SetItem(index, 2, db_obj.description)
            self.SetItem(index, 3, db_obj.family.name)
            self.SetItem(index, 4, db_obj.series.name)
            self.SetItemData(index, db_obj)
            self.CheckItem(index, is_checked)

        self.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.SetColumnWidth(1, wx.LIST_AUTOSIZE)
        self.SetColumnWidth(2, wx.LIST_AUTOSIZE)
        self.SetColumnWidth(3, wx.LIST_AUTOSIZE)
        self.SetColumnWidth(4, wx.LIST_AUTOSIZE)


class AccessoryPicker(_popupctrl.PopupControl):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        self.global_db = global_db

        _popupctrl.PopupControl.__init__(self, parent, wx.ID_ANY)

        self.win = wx.Window(self, wx.ID_ANY, pos=(0, 0), style=0)
        self.ctrl = CheckListCtrl(self.win)

        bz = self.ctrl.GetBestSize()
        self.win.SetSize(bz)

        self.SetPopupContent(self.win)

        self.ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.ctrl.Bind(wx.EVT_LIST_ITEM_CHECKED, self.on_item_checked)
        self.ctrl.Bind(wx.EVT_LIST_ITEM_UNCHECKED, self.on_item_unchecked)
        self.ctrl.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.on_right_click)

    def reset_items(self):
        value = _popupctrl.PopupControl.GetValue(self)
        value = value.split(', ')

        res = []
        for accessory in self.global_db.accessories_table:
            pn = accessory.part_number
            checked = pn in value

            res.append((accessory, checked))

        self.ctrl.SetItems(res)

    def on_right_click(self, evt):
        index = evt.Index
        x, y = evt.GetPosition()
        db_obj = self.ctrl.GetItemData(index)

        menu = wx.Menu()

        menu_item = menu.Append('Edit Accessory')
        item_id = menu_item.GetId()

        def _on_edit(event):
            dlg = AccessoryDialog(self.GetTopLevelParent(), self.global_db, db_obj)
            try:
                if dlg.ShowModal() == wx.ID_OK:
                    dlg.GetValue()
                    self.reset_items()
            finally:
                dlg.Destroy()

            event.Skip()

        self.Bind(wx.EVT_MENU, _on_edit, id=item_id)

        self.PopupMenu(menu, x, y)

    def on_item_activated(self, evt):
        index = evt.Index
        db_obj = self.ctrl.GetItemData(index)

        dlg = AccessoryDialog(self.GetTopLevelParent(), self.global_db, db_obj)

        try:
            if dlg.ShowModal() == wx.ID_OK:
                dlg.GetValue()
                self.reset_items()
        finally:
            dlg.Destroy()

        evt.Skip()

    def on_item_checked(self, evt):
        index = evt.Index
        db_obj = self.ctrl.GetItemData(index)
        value = _popupctrl.PopupControl.GetValue(self)
        value = value.split(', ')

        pn = db_obj.part_number  # NOQA
        if pn not in value:
            value.append(pn)

        _popupctrl.PopupControl.SetValue(self, ', '.join(value))
        evt.Skip()

    def on_item_unchecked(self, evt):
        index = evt.Index
        db_obj = self.ctrl.GetItemData(index)
        value = _popupctrl.PopupControl.GetValue(self)
        value = value.split(', ')

        pn = db_obj.part_number  # NOQA
        if pn in value:
            value.remove(pn)

        _popupctrl.PopupControl.SetValue(self, ', '.join(value))
        evt.Skip()

    def GetValue(self) -> list[str]:
        value = _popupctrl.PopupControl.GetValue(self)
        value = value.split(', ')
        return value

    def SetValue(self, value: list[_accessory.Accessory]):
        value = [v.part_number for v in value]
        _popupctrl.PopupControl.SetValue(self, ', '.join(value))

    def FormatContent(self):
        self.reset_items()


class AccessoryDialog(wx.Dialog):

    def __init__(self, parent, global_db: _global_db.GLBTables, db_obj: _accessory.Accessory | None):

        wx.Dialog.__init__(self, parent)
        self.global_db = global_db

        self.pn_ctrl = _part_numberctrl.PartNumberCtrl(self)
        self.mfg_ctrl = _manufacturerctrl.ManufacturerCtrl(self, global_db)
        self.desc_ctrl = _descriptionctrl.DescriptionCtrl(self)
        self.family_ctrl = _familyctrl.FamilyCtrl(self, global_db)
        self.series_ctrl = _seriesctrl.SeriesCtrl(self, global_db)
        self.color_ctrl = _colorctrl.ColorCtrl(self, global_db, 'Color:')
        self.material_ctrl = _materialctrl.MaterialCtrl(self, global_db)

        self.db_obj = db_obj

        if db_obj is not None:
            self.pn_ctrl.SetValue(db_obj.part_number)
            self.desc_ctrl.SetValue(db_obj.description)
            self.family_ctrl.SetDBObject(db_obj.family)
            self.mfg_ctrl.SetDBObject(db_obj.manufacturer)
            self.series_ctrl.SetDBObject(db_obj.series)
            self.color_ctrl.SetDBObject(db_obj.color)
            self.material_ctrl.SetDBObject(db_obj.material)

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(self.pn_ctrl)
        sizer.Add(self.mfg_ctrl)
        sizer.Add(self.desc_ctrl)
        sizer.Add(self.family_ctrl)
        sizer.Add(self.series_ctrl)
        sizer.Add(self.color_ctrl)
        sizer.Add(self.material_ctrl)

        self.SetSizer(sizer)

    def GetValue(self) -> int:
        pn = self.pn_ctrl.GetValue()
        mfg_id = self.mfg_ctrl.GetValue()
        desc = self.desc_ctrl.GetValue()
        family_id = self.family_ctrl.GetValue()
        series_id = self.series_ctrl.GetValue()
        color_id = self.color_ctrl.GetValue()
        material_id = self.material_ctrl.GetValue()

        if self.db_obj is not None:
            self.global_db.accessories_table.update(
                self.db_obj.db_id, part_number=pn, description=desc, mfg_id=mfg_id,
                family_id=family_id, series_id=series_id, material_id=material_id,
                color_id=color_id)

        else:
            self.db_obj = self.global_db.accessories_table.insert(
                part_number=pn, description=desc, mfg_id=mfg_id, family_id=family_id,
                series_id=series_id, material_id=material_id, color_id=color_id)

        return self.db_obj.db_id


class AccessoryCtrl(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        self.global_db = global_db

        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        self.choice_ctrl = AccessoryPicker(self, global_db)
        self.new_button = wx.Button('New Accessory', size=(40, -1))

        self.new_button.Bind(wx.EVT_BUTTON, self.on_new_button)

        sizer = utils.HSizer(self, 'Accessories:', self.choice_ctrl, None, self.new_button)
        self.SetSizer(sizer)

    def on_new_button(self, evt):
        dlg = AccessoryDialog(self.GetTopLevelParent(), self.global_db, None)

        try:
            if dlg.ShowModal() == wx.ID_OK:
                db_id = dlg.GetValue()
                accessory = self.global_db.accessories_table[db_id]
                pn = accessory.part_number
                value = self.choice_ctrl.GetValue()
                value.append(pn)
                value = [self.global_db.accessories_table[pn] for pn in value]
                self.choice_ctrl.SetValue(value)
        finally:
            dlg.Destroy()

        evt.Skip()

    def SetValue(self, value: list[_accessory.Accessory]):
        self.choice_ctrl.SetValue(value)

    def GetValue(self) -> list[str]:
        return self.choice_ctrl.GetValue()
