
import wx
from wx.lib import expando as _expando

from ... import utils
from ...widgets import autocomplete_combobox as _ac_combobox
from ...database import global_db as _global_db
from ...database.global_db import manufacturer as _manufacturer
from . import descriptionctrl as _descriptionctrl


'''

name str
description str
address str
contact_person str
phone str
ext str
email str
website str

'''


class ManufacturerCtrl(wx.Panel):

    def __init__(self, parent, global_db: _global_db.GLBTables):
        self.global_db = global_db
        wx.Panel.__init__(self, parent, wx.ID_ANY, style=wx.BORDER_NONE)

        choices = global_db.manufacturers_table.choices

        sb_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, 'Manufacturer')
        sb = sb_sizer.GetStaticBox()

        self.choice_ctrl = _ac_combobox.AutoCompleteComboBox(sb, choices=choices, size=(250, -1))
        self.choice_ctrl.SetValue('')

        self.desc_ctrl = _descriptionctrl.DescriptionCtrl(sb)
        self.addr_ctrl = _expando.ExpandoTextCtrl(sb, wx.ID_ANY, size=(250, -1))
        self.contact_ctrl = wx.TextCtrl(sb, wx.ID_ANY, size=(200, -1))
        self.phone_ctrl = wx.TextCtrl(sb, wx.ID_ANY, size=(100, -1))
        self.ext_ctrl = wx.TextCtrl(sb, wx.ID_ANY, size=(100, -1))
        self.email_ctrl = wx.TextCtrl(sb, wx.ID_ANY, size=(200, -1))
        self.website_ctrl = wx.TextCtrl(sb, wx.ID_ANY, size=(200, -1))

        self.mfg_db_obj = None
        self.choice_ctrl.Bind(wx.EVT_COMBOBOX, self.on_choice)

        choice_sizer = utils.HSizer(sb, 'Name:', self.choice_ctrl)
        desc_sizer = utils.HSizer(sb, None, self.desc_ctrl)
        addr_sizer = utils.HSizer(sb, None, 'Address:', self.addr_ctrl)
        contact_sizer = utils.HSizer(sb, None, 'Contact:', self.contact_ctrl)
        phone_sizer = utils.HSizer(sb, None, 'Phone:', self.phone_ctrl)
        ext_sizer = utils.HSizer(sb, None, 'Ext:', self.ext_ctrl)
        email_sizer = utils.HSizer(sb, None, 'Email:', self.email_ctrl)
        website_sizer = utils.HSizer(sb, None, 'Website:', self.website_ctrl)

        sb_sizer.Add(choice_sizer)
        sb_sizer.Add(desc_sizer)
        sb_sizer.Add(addr_sizer)
        sb_sizer.Add(contact_sizer)
        sb_sizer.Add(phone_sizer)
        sb_sizer.Add(ext_sizer)
        sb_sizer.Add(email_sizer)
        sb_sizer.Add(website_sizer)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(sb_sizer)

        self.SetSizer(sizer)

    def on_choice(self, evt: wx.CommandEvent):
        index = self.choice_ctrl.GetSelection()
        name = self.choice_ctrl.GetString(index)
        self.mfg_db_obj = self.global_db.manufacturers_table[name]
        self.desc_ctrl.SetValue(self.mfg_db_obj.description)
        self.addr_ctrl.SetValue(self.mfg_db_obj.address)
        self.contact_ctrl.SetValue(self.mfg_db_obj.contact_person)
        self.phone_ctrl.SetValue(self.mfg_db_obj.phone)
        self.ext_ctrl.SetValue(self.mfg_db_obj.ext)
        self.email_ctrl.SetValue(self.mfg_db_obj.email)
        self.website_ctrl.SetValue(self.mfg_db_obj.website)

        evt.Skip()

    def SetDBObject(self, db_obj: _manufacturer.Manufacturer) -> None:
        self.mfg_db_obj = db_obj
        self.choice_ctrl.SetValue(db_obj.name)
        self.desc_ctrl.SetValue(self.mfg_db_obj.description)
        self.addr_ctrl.SetValue(self.mfg_db_obj.address)
        self.contact_ctrl.SetValue(self.mfg_db_obj.contact_person)
        self.phone_ctrl.SetValue(self.mfg_db_obj.phone)
        self.ext_ctrl.SetValue(self.mfg_db_obj.ext)
        self.email_ctrl.SetValue(self.mfg_db_obj.email)
        self.website_ctrl.SetValue(self.mfg_db_obj.website)

    def GetValue(self) -> int:
        name = self.choice_ctrl.GetValue()

        try:
            return self.global_db.manufacturers_table[name].db_id
        except KeyError:
            return self.global_db.manufacturers_table.insert(
                name,
                self.desc_ctrl.GetValue(),
                self.addr_ctrl.GetValue(),
                self.contact_ctrl.GetValue(),
                self.phone_ctrl.GetValue(),
                self.ext_ctrl.GetValue(),
                self.email_ctrl.GetValue(),
                self.website_ctrl.GetValue()
            ).db_id
