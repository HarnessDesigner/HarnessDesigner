import os
import sys
import wx


def get_appdata():
    user_profile = os.path.expanduser('~')

    if sys.platform.startswith('win'):
        app_data = os.path.join('appdata', 'roaming', 'HarnessMaker')
    else:
        app_data = '.HarnessMaker'

    app_data = os.path.join(user_profile, app_data)
    if not os.path.exists(app_data):
        os.mkdir(app_data)

    return app_data


def remap(value, old_min, old_max, new_min, new_max):
    old_range = old_max - old_min
    new_range = new_max - new_min
    new_value = (((value - old_min) * new_range) / old_range) + new_min
    return new_value


class HSizer(wx.BoxSizer):

    def __init__(self, parent, text, ctrl):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        if text is not None:
            st = wx.StaticText(parent, wx.ID_ANY, label=text)
            self.Add(st, 0, wx.ALL, 5)

        self.Add(ctrl, 0, wx.ALL, 5)
