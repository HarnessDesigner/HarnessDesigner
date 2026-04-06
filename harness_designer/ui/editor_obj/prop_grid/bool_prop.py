
from wx import propgrid as wxpg


class BoolProperty(wxpg.BoolProperty):

    def __init__(self, label, name, value, use_checkbox=True):
        wxpg.BoolProperty.__init__(label, name, value)

        if use_checkbox:
            self.SetAttribute(wxpg.PG_BOOL_USE_CHECKBOX, True)
