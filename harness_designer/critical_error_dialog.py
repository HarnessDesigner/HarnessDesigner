import wx
import traceback


class CriticalErrorDialog(wx.Dialog):

    def __init__(self, parent, err):
        message = ''.join(traceback.format_exception(err))

        caption = (
            'A critical error has occured...\n\n'
            'Please report this error to\n'
            'https://github.com/HarnessDesigner/HarnessDesigner/issues\n'
        )

        wx.Dialog.__init__(self, parent, wx.ID_ANY, title='Critical Error', size=(400, 600),
                           style=wx.STAY_ON_TOP | wx.CAPTION | wx.CLOSE_BOX)

        err_msg = wx.TextCtrl(self, wx.ID_ANY, value=message, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_DONTWRAP)

        style = wx.ART_ERROR
        icon = wx.ArtProvider.GetBitmap(style, wx.ART_MESSAGE_BOX)
        icon = wx.StaticBitmap(self, wx.ID_ANY, bitmap=icon)
        caption = wx.StaticText(self, wx.ID_ANY, label=caption)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        vsizer = wx.BoxSizer(wx.VERTICAL)
        hsizer.Add(icon, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 20)
        hsizer.Add(caption, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 20)
        vsizer.Add(hsizer, 0)
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(err_msg, 1, wx.EXPAND | wx.ALL, 10)
        vsizer.Add(hsizer, 1, wx.EXPAND)

        button_sizer = self.CreateSeparatedButtonSizer(wx.OK)
        vsizer.Add(button_sizer, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(vsizer)
        self.CenterOnParent()
