
import wx
from wx.lib import expando as _expando
from wx.lib import masked as _masked
import wx.lib.masked.maskededit


from . import AttributePanel
from ..widgets import auto_complete as _auto_complete


class ConnectorAttrPanel(AttributePanel):

    def __init__(self, parent, mfg_data):
        AttributePanel.__init__(self, parent)

        choices = mfg_data.table.select('name')

        self.mfg_data = mfg_data
        self.original_mfg_data = mfg_data

        self.name_ctrl = _auto_complete.AutoComplete(self, wx.ID_ANY, value='', autocomplete_choices=[])
        self.desc_ctrl = _expando.ExpandoTextCtrl(self, wx.ID_ANY, value='')
        self.address_ctrl = _expando.ExpandoTextCtrl(self, wx.ID_ANY, value='')
        self.contact_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(50, -1))
        self.phone_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(50, -1))
        self.ext_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(20, -1))
        self.email_ctrl = _masked.TextCtrl(self, -1, value='', **wx.lib.masked.maskededit.masktags['EMAIL'])
        self.website_ctrl = wx.TextCtrl(self, wx.ID_ANY, value='', size=(50, -1))
        self.save_button = wx.Button(self, wx.ID_ANY, label="Save")
        self.revert_button = wx.Button(self, wx.ID_ANY, label="Undo Changes")

        self.save_button.Enable(False)
        self.revert_button.Enable(False)

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
        self.mfg_data = data

    def _on_change(self, evt):

        def _do():

            if self.original_mfg_data != self.mfg_data:
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
