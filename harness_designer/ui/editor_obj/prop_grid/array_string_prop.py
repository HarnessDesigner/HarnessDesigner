from wx import propgrid as wxpg


class ArrayStringProperty(wxpg.ArrayStringProperty):

    def __init__(self, label, name, value):
        value = ', '.join(value)

        wxpg.ArrayStringProperty.__init__(self, label, name, value)

        self.SetAttribute(wxpg.PG_ARRAY_DELIMITER, ', ')
        self.SetAttribute(wxpg.PG_DIALOG_TITLE, f'Set {label}')

    def GetValue(self):
        value = wxpg.ArrayStringProperty.GetValue(self)
        return value.split(', ')
