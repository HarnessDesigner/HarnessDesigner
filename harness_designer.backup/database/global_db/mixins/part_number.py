from .base import BaseMixin

import wx


class PartNumberMixin(BaseMixin):

    @property
    def part_number(self) -> str:
        return self._table.select('part_number', id=self._db_id)[0][0]

    def ui_controls(self, parent: wx.Window) -> "PartNumberControl":
        return PartNumberControl(parent, self)


class PartNumberControl(wx.BoxSizer):

    def __init__(self, parent, db_obj: PartNumberMixin):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        label = wx.StaticText(parent, wx.ID_ANY, label='Part Number:')
        ctrl = wx.TextCtrl(parent, wx.ID_ANY, value=db_obj.part_number)
        ctrl.Enable(False)
        self.Add(label, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 5)
        self.Add(ctrl, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)

    def Save(self):
        pass
