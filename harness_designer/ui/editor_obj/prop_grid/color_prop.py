from wx import propgrid as wxpg


class ColorProperty(wxpg.ColourProperty):

    def __init__(self, label, name, value):
        wxpg.ColourProperty.__init__(self, label, name, value)

        self.SetAttribute(wxpg.PG_COLOUR_ALLOW_CUSTOM, True)
        self.SetAttribute(wxpg.PG_COLOUR_HAS_ALPHA, True)
