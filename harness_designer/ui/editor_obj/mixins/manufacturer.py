from typing import TYPE_CHECKING

import wx
from . import mixinbase as _mixinbase

if TYPE_CHECKING:
    from ....database.global_db import manufacturer as _manufacturer


class ManufacturerMixin(_mixinbase.MixinBase):

    def __init__(self, db_obj: "_manufacturer.Manufacturer"):
        _mixinbase.MixinBase.__init__(self)

        fold_panel = self.AddFoldPanel('Manufacturer', collapsed=True)

        panel = wx.Panel(fold_panel, wx.ID_ANY, style=wx.BORDER_NONE)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        def hsizer(label, data):
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            st1 = wx.StaticText(panel, wx.ID_ANY, label)
            st2 = wx.StaticText(panel, wx.ID_ANY, data)

            sizer.Add(st1, 1, wx.ALL | wx.ALIGN_TOP, 3)
            sizer.Add(st2, 1, wx.ALL, 3)
            vsizer.Add(sizer, 1)

        hsizer('Name:', db_obj.name)
        hsizer('Description:', db_obj.description)
        hsizer('Address:', db_obj.address)
        hsizer('Contact:', db_obj.contact_person)
        hsizer('Phone:', db_obj.phone + ' : ' + db_obj.ext)
        hsizer('Email:', db_obj.email)
        hsizer('Website:', db_obj.website)

        panel.SetSizer(vsizer)
        self.AddFoldPanelWindow(fold_panel, panel)

