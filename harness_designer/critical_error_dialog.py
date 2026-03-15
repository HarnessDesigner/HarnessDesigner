import wx
import traceback


class CriticalErrorDialog(wx.MessageDialog):

    def __init__(self, parent, err):
        message = ''.join(traceback.format_exception(err))

        message = (
            'A critical error has occured...\n\n'
            f'{message}\n'
            'Please report this error to\n'
            'https://github.com/HarnessDesigner/HarnessDesigner/issues\n'
        )

        wx.MessageDialog.__init__(self, parent, message=message, caption='Critical Error',
                                  style=wx.ICON_ERROR | wx.STAY_ON_TOP | wx.CENTRE | wx.OK | wx.OK_DEFAULT)
