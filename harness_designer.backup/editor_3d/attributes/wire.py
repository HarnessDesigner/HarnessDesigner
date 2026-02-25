
import wx
from wx.lib import expando as _expando
from wx.lib import masked as _masked
import wx.lib.masked.maskededit


from . import AttributePanel
from ..widgets import auto_complete as _auto_complete


class WireAttrPanel(AttributePanel):

    def __init__(self, parent):
        AttributePanel.__init__(self, parent)

        self._data = None
        self._original_data = None

        self.name_ctrl = _auto_complete.AutoComplete(self, wx.ID_ANY, value='', autocomplete_choices=[])
        self.desc_ctrl = _expando.ExpandoTextCtrl(self, wx.ID_ANY, value='')
        self.address_ctrl = _expando.ExpandoTextCtrl(self, wx.ID_ANY, value='')
        self.contact_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(50, -1))
        self.phone_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(50, -1))
        self.ext_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(20, -1))
        self.email_ctrl = _masked.TextCtrl(self, -1, value='', **wx.lib.masked.maskededit.masktags['EMAIL'])
        self.website_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(50, -1))

        self.name_ctrl.Bind(wx.EVT_CHAR, self._on_change)
        self.desc_ctrl.Bind(wx.EVT_CHAR, self._on_change)
        self.address_ctrl.Bind(wx.EVT_CHAR, self._on_change)
        self.contact_ctrl.Bind(wx.EVT_CHAR, self._on_change)
        self.ext_ctrl.Bind(wx.EVT_CHAR, self._on_change)
        self.email_ctrl.Bind(wx.EVT_CHAR, self._on_change)
        self.website_ctrl.Bind(wx.EVT_CHAR, self._on_change)
        self.name_ctrl.Bind(wx.EVT_CHAR, self._on_name)

        self.AddItems(('Name:', self.name_ctrl),
                      ('Description:', self.desc_ctrl),
                      ('Address:', self.address_ctrl),
                      ('Contact:', self.contact_ctrl),
                      ('Phone:', self.phone_ctrl),
                      ('ext:', self.ext_ctrl),
                      ('E-Mail:', self.email_ctrl),
                      ('Website:', self.website_ctrl))

    def SetData(self, data):
        self._data = data

    def _on_change(self, evt):

        def _do():

            if self._original_data != self._data:
                self.save_button.Enable(True)
                self.revert_button.Enable(True)
            else:
                flag = (
                    self.mfg_data.name != self.name_ctrl.GetValue() or
                    self.mfg_data.description != self.desc_ctrl.GetValue() or
                    self.mfg_data.address != self.address_ctrl.GetValue() or
                    self.mfg_data.contact != self.contact_ctrl.GetValue() or
                    self.mfg_data.phone != self.phone_ctrl.GetValue() or
                    self.mfg_data.ext != self.ext_ctrl.GetValue() or
                    self.mfg_data.email != self.email_ctrl.GetValue() or
                    self.mfg_data.website != self.website_ctrl.GetValue()
                )
                self.save_button.Enable(flag)
                self.revert_button.Enable(flag)

        wx.CallAfter(_do)
        evt.Skip()

    def _on_name(self, evt):
        def _do():
            value = self.name_ctrl.GetValue()
            if value in self.choices:
                self.mfg_data = self.mfg_data.table[value]
                self.desc_ctrl.SetValue(self.mfg_data.description)
                self.address_ctrl.SetValue(self.mfg_data.address)
                self.contact_ctrl.SetValue(self.mfg_data.contact_person)
                self.phone_ctrl.SetValue(self.mfg_data.phone)
                self.ext_ctrl.SetValue(self.mfg_data.ext)
                self.email_ctrl.SetValue(self.mfg_data.email)
                self.website_ctrl.SetValue(self.mfg_data.website)
            else:
                self.desc_ctrl.SetValue('')
                self.address_ctrl.SetValue('')
                self.contact_ctrl.SetValue('')
                self.phone_ctrl.SetValue('')
                self.ext_ctrl.SetValue('')
                self.email_ctrl.SetValue('')
                self.website_ctrl.SetValue('')

        wx.CallAfter(_do)
        evt.Skip()
