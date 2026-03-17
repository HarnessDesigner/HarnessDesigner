
from typing import TYPE_CHECKING

import wx

from . import dialog_base as _dialog_base
from ..widgets import text_ctrl as _text_ctrl

if TYPE_CHECKING:
    from ...database.global_db import manufacturer as _manufacturer


class AddManufacturerDialog(_dialog_base.BaseDialog):

    def __init__(self, parent, name, table: "_manufacturer.ManufacturersTable"):

        self.table = table
        _dialog_base.BaseDialog.__init__(self, parent, 'Add to Database', label='Add Manufacturer')

        self.name = _text_ctrl.TextCtrl(self.panel, 'Name:', (-1, -1), style=wx.TE_READONLY)
        self.name.SetValue(name)

        self.description = _text_ctrl.TextCtrl(self.panel, 'Description:', (-1, -1), style=wx.TE_MULTILINE)
        self.address = _text_ctrl.TextCtrl(self.panel, 'Address:', (-1, -1), style=wx.TE_MULTILINE)
        self.contact = _text_ctrl.TextCtrl(self.panel, 'Contact Person:', (-1, -1))
        self.phone = _text_ctrl.TextCtrl(self.panel, 'Phone Number:', (-1, -1))
        self.ext = _text_ctrl.TextCtrl(self.panel, 'ext:', (-1, -1))
        self.email = _text_ctrl.TextCtrl(self.panel, 'EMail:', (-1, -1))
        self.website = _text_ctrl.TextCtrl(self.panel, 'Website:', (-1, -1))

        vsizer = wx.BoxSizer(wx.VERTICAL)

        def _add(ctrl1, ctrl2=None):
            hsizer = wx.BoxSizer(wx.HORIZONTAL)

            if ctrl2 is None:
                hsizer.Add(ctrl1, 1, wx.EXPAND)
            else:
                hsizer.Add(ctrl1, 3, wx.EXPAND)
                hsizer.Add(ctrl2, 1, wx.EXPAND)

            vsizer.Add(hsizer, 1, wx.EXPAND)

        _add(self.name)
        _add(self.description)
        _add(self.address)
        _add(self.contact)
        _add(self.phone, self.ext)
        _add(self.email)
        _add(self.website)

        self.panel.SetSizer(vsizer)

    def GetValue(self):
        name = self.name.GetValue()
        description = self.description.GetValue().strip()
        address = self.address.GetValue().strip()
        contact = self.contact.GetValue().strip()
        phone = self.phone.GetValue().strip()
        ext = self.ext.GetValue().strip()
        email = self.email.GetValue().strip()
        website = self.website.GetValue().strip()
        return name, description, address, contact, phone, ext, email, website
