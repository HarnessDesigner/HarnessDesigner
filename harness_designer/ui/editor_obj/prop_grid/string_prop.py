from wx import propgrid as wxpg


class StringProperty(wxpg.StringProperty):

    def __init__(self, label, name, value, units=None):

        wxpg.StringProperty.__init__(self, label, name, value)

        if units is not None:
            self.SetAttribute(wxpg.PG_ATTR_UNITS, units)

